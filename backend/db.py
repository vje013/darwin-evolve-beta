"""
Darwin Enterprise Evolve Beta — Database Layer
SQLite for operational data. Neo4j for the graph.
"""
import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.getenv("DATABASE_URL", "sqlite:///./darwin.db").replace("sqlite:///", "")


def get_db_path():
    return DATABASE_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables on first boot."""
    with get_db() as conn:
        conn.executescript("""
            -- Users
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            -- Rooms
            CREATE TABLE IF NOT EXISTS rooms (
                room_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                default_model TEXT NOT NULL DEFAULT 'anthropic/claude-sonnet-4',
                budget_cap_monthly REAL DEFAULT NULL,
                strict_citations INTEGER DEFAULT 0,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (created_by) REFERENCES users(user_id)
            );

            -- Room Members
            CREATE TABLE IF NOT EXISTS room_members (
                room_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('owner', 'admin', 'member', 'viewer')),
                joined_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (room_id, user_id),
                FOREIGN KEY (room_id) REFERENCES rooms(room_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Messages
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                author_id TEXT NOT NULL,
                author_type TEXT NOT NULL DEFAULT 'human' CHECK(author_type IN ('human', 'ai', 'system')),
                content TEXT NOT NULL,
                thread_id TEXT DEFAULT NULL,
                model_used TEXT DEFAULT NULL,
                tokens_in INTEGER DEFAULT NULL,
                tokens_out INTEGER DEFAULT NULL,
                cost REAL DEFAULT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            );

            -- Model Invocations (denormalized for quick spend queries)
            CREATE TABLE IF NOT EXISTS model_invocations (
                invocation_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens_in INTEGER NOT NULL,
                tokens_out INTEGER NOT NULL,
                cost REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            );

            -- Connector configs per room
            CREATE TABLE IF NOT EXISTS connectors (
                connector_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                connector_type TEXT NOT NULL CHECK(connector_type IN ('github', 'figma', 'trello', 'teams')),
                config TEXT NOT NULL DEFAULT '{}',
                last_synced_at TEXT DEFAULT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            );

            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
            CREATE INDEX IF NOT EXISTS idx_room_members_user ON room_members(user_id);
            CREATE INDEX IF NOT EXISTS idx_invocations_room ON model_invocations(room_id, created_at);

            CREATE TABLE IF NOT EXISTS training_jobs (
        job_id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'queued',
        progress INTEGER NOT NULL DEFAULT 0,
        message TEXT,
        model_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        completed_at TEXT,
        created_by TEXT
    );

    CREATE TABLE IF NOT EXISTS trained_models (
        model_id TEXT PRIMARY KEY,
        tinker_model_id TEXT,
        base_model TEXT NOT NULL,
        lora_rank INTEGER NOT NULL DEFAULT 32,
        training_examples INTEGER,
        final_loss REAL,
        status TEXT NOT NULL DEFAULT 'training',
        created_at TEXT NOT NULL,
        job_id TEXT
    ); """)
    print("✅ SQLite initialized")
