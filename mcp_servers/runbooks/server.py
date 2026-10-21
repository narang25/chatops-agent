"""
search_runbooks MCP Server (mcp v2 / MCPServer API).

Exposes a single tool: search_runbooks(query, top_k)
Shape matches contracts/mcp_tools.md exactly.

Run via stdio transport:
    python -m mcp_servers.runbooks.server
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is importable regardless of cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.mcpserver import MCPServer
from rag.ingest import query_runbooks, DEFAULT_DB_PATH

mcp = MCPServer(
    name="chatops-runbooks",
    version="1.0.0",
    description="Search SRE runbooks via semantic similarity (Chroma + all-MiniLM-L6-v2).",
)


@mcp.tool(
    description=(
        "Search the ChatOps runbook knowledge base using a natural-language query. "
        "Returns the top-k most relevant runbook snippets with metadata and similarity scores. "
        "Use this tool first when diagnosing any service incident."
    )
)
def search_runbooks(query: str, top_k: int = 3) -> dict:
    """
    Search runbooks for the given query.

    Args:
        query:  Natural-language description of the incident or symptom.
        top_k:  Number of results to return (default 3, max 10).

    Returns:
        Contract shape from contracts/mcp_tools.md:
        {
            "query": str,
            "results": [
                {
                    "title": str,
                    "source": str,
                    "failure_type": str,
                    "service": str,
                    "score": float,
                    "snippet": str
                }
            ]
        }
    """
    try:
        top_k = max(1, min(int(top_k), 10))
        chunks = query_runbooks(query, db_path=DEFAULT_DB_PATH, top_k=top_k)
        results = [
            {
                "title": c["title"],
                "source": c["source"],
                "failure_type": c["failure_type"],
                "service": c["service"],
                "score": c["score"],
                "snippet": c["snippet"][:400],  # Trim for MCP transport
            }
            for c in chunks
        ]
        return {"query": query, "results": results}
    except Exception as exc:
        return {"error": f"search_runbooks failed: {exc}"}


if __name__ == "__main__":
    mcp.run_stdio_async()
