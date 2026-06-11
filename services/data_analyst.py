"""
Darwin Enterprise Evolve Beta — Data Analyst Agent Service
Natural language SQL queries against uploaded CSV datasets via Claude.
"""
import os
import re
import uuid
import pandas as pd
from sqlalchemy import create_engine, text
import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Store active database sessions
_active_dbs = {}


def _get_anthropic_client():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)


def load_csv_to_db(csv_bytes: bytes, filename: str) -> dict:
    """Load a CSV file into a SQLite database and return session info."""
    table_name = re.sub(r'[^a-zA-Z0-9]', '_', os.path.splitext(filename)[0])
    db_id = str(uuid.uuid4())[:8]
    db_path = f"/tmp/analyst_{db_id}.db"

    engine = create_engine(f"sqlite:///{db_path}")
    df = pd.read_csv(pd.io.common.BytesIO(csv_bytes))
    df.to_sql(table_name, engine, index=False, if_exists='replace')

    # Get schema info
    columns = list(df.columns)
    dtypes = {col: str(df[col].dtype) for col in columns}
    sample_rows = df.head(3).to_dict(orient='records')

    _active_dbs[db_id] = {
        "engine": engine,
        "table_name": table_name,
        "columns": columns,
        "dtypes": dtypes,
        "row_count": len(df),
        "db_path": db_path,
    }

    return {
        "db_id": db_id,
        "table_name": table_name,
        "columns": columns,
        "dtypes": dtypes,
        "row_count": len(df),
        "sample_rows": sample_rows,
    }


def query_data(db_id: str, natural_query: str) -> dict:
    """Convert natural language to SQL, execute, return results."""
    if db_id not in _active_dbs:
        return {"error": "Database session not found. Please upload a CSV first."}

    db_info = _active_dbs[db_id]
    engine = db_info["engine"]
    table_name = db_info["table_name"]
    columns = db_info["columns"]
    dtypes = db_info["dtypes"]

    client = _get_anthropic_client()

    # Step 1: Generate SQL from natural language
    schema_desc = "\n".join(f"  - {col} ({dtypes[col]})" for col in columns)

    sql_prompt = f"""You are a SQL expert. Convert this natural language question to a SQLite query.

Table name: {table_name}
Columns:
{schema_desc}
Row count: {db_info['row_count']}

Question: {natural_query}

Return ONLY the SQL query, nothing else. No markdown, no explanation."""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": sql_prompt}]
        )
        sql_query = msg.content[0].text.strip()
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
    except Exception as e:
        return {"error": f"Failed to generate SQL: {e}"}

    # Step 2: Execute SQL
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = [dict(row._mapping) for row in result]
    except Exception as e:
        return {"error": f"SQL execution failed: {e}", "sql": sql_query}

    # Step 3: Generate natural language answer
    try:
        result_preview = str(rows[:10]) if rows else "No results"
        answer_prompt = f"""Based on this SQL query and results, provide a clear, concise answer to the user's question.

Question: {natural_query}
SQL: {sql_query}
Results: {result_preview}
Total rows returned: {len(rows)}

Give a natural language answer. Be specific with numbers. Keep it concise."""

        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": answer_prompt}]
        )
        answer = msg.content[0].text
    except Exception:
        answer = f"Query returned {len(rows)} rows."

    return {
        "sql": sql_query,
        "answer": answer,
        "rows": rows[:50],  # Limit to 50 rows for response size
        "total_rows": len(rows),
    }
