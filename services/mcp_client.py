"""
Darwin Enterprise Evolve — MongoDB MCP Client
Connects to @mongodb-js/mongodb-mcp-server via subprocess stdin/stdout.
"""
import subprocess
import json
import os
import threading

_process = None
_lock = threading.Lock()
_request_id = 0


def _get_process():
    global _process
    if _process is None or _process.poll() is not None:
        mongo_uri = os.getenv("MONGO_URI", "")
        _process = subprocess.Popen(
            ["npx", "-y", "@mongodb-js/mongodb-mcp-server", "--connectionString", mongo_uri],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Read the startup notification
        _read_response()
    return _process


def _send_request(method, params=None):
    global _request_id
    with _lock:
        _request_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": _request_id,
            "method": method,
        }
        if params:
            req["params"] = params

        proc = _get_process()
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        return _read_response()


def _read_response():
    proc = _get_process()
    line = proc.stdout.readline().strip()
    if line:
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON: {line[:200]}"}
    return {"error": "No response"}


def mcp_list_tools():
    """List available MCP tools from MongoDB server."""
    return _send_request("tools/list")


def mcp_call_tool(tool_name, arguments):
    """Call an MCP tool on the MongoDB server."""
    return _send_request("tools/call", {
        "name": tool_name,
        "arguments": arguments,
    })


def test_mcp_connection():
    """Test that MCP server is running and responsive."""
    try:
        result = mcp_list_tools()
        if "result" in result:
            tools = result["result"].get("tools", [])
            return {"status": "ok", "tools": [t.get("name") for t in tools]}
        return {"status": "error", "detail": str(result)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
