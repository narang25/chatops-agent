# mcp_servers/runbooks — `search_runbooks` MCP Server

Exposes the `search_runbooks` tool over the **Model Context Protocol (MCP) stdio transport** so that any MCP-aware agent (LangGraph, Claude Desktop, Cursor, etc.) can query the ChatOps runbook knowledge base.

---

## Tool contract

```
search_runbooks(query: str, top_k: int = 3) -> {
  "query": str,
  "results": [
    {"title": str, "source": str, "failure_type": str,
     "service": str, "score": float, "snippet": str}
  ]
}
```

Errors are returned as `{"error": "<message>"}` — the agent reads them and reacts.

---

## Prerequisites

- Virtual environment activated (`source .venv/bin/activate`).
- Chroma DB already indexed: `python rag/ingest.py`.

---

## Run

```bash
# From the project root (stdio transport — used by agents and MCP clients)
python -m mcp_servers.runbooks.server
```

The server reads JSON-RPC messages from stdin and writes responses to stdout (MCP stdio protocol).

---

## Quick smoke test

```bash
# Verify the tool is registered
python - <<'EOF'
import asyncio, json, sys
from mcp_servers.runbooks.server import mcp

async def test():
    result = mcp.call_tool("search_runbooks", {"query": "container OOMKilled exit code 137"})
    data = await result if asyncio.iscoroutine(result) else result
    print(json.dumps(data, indent=2))

asyncio.run(test())
EOF
```

Expected: JSON with `"query"` and `"results"` array where the top hit has `"failure_type": "out_of_memory"`.
