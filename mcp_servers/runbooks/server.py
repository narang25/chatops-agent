"""
search_runbooks MCP Server (mcp v2 / MCPServer API).

Exposes a single tool: search_runbooks(query, top_k, include_external)
Shape matches contracts/mcp_tools.md exactly.

Weeks 4-5 updates:
- Confidence threshold (0.60) and `no_confident_match` flag for unknown handling (Task A16).
- Dual-collection search across internal runbooks and external knowledge (Task A17).
- Internal runbooks rank first; ties broken in favor of internal.
- External results tagged with source_type (external_postmortem / external_doc) and source_url.
- Deduplication by document title to ensure diverse top-k references.

Run via stdio transport:
    python -m mcp_servers.runbooks.server
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable regardless of cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.mcpserver import MCPServer

from rag.ingest import DEFAULT_DB_PATH, query_runbooks
from rag.ingest_external import query_external_docs

mcp = MCPServer(
    name="chatops-runbooks",
    version="2.1.0",
    description="Search internal SRE runbooks and external failure knowledge via Chroma semantic similarity.",
)

# Similarity score below which we flag "no confident match".
# Scores from rag/ingest are 1 / (1 + distance), so identical = 1.0,
# orthogonal = ~0.50. Known failure queries score 0.65 - 0.77.
# A threshold of 0.60 cleanly separates known runbooks from novel/gibberish queries.
CONFIDENCE_THRESHOLD = 0.60


@mcp.tool(
    description=(
        "Search the ChatOps runbook knowledge base using a natural-language query. "
        "Searches both internal playbooks and external failure knowledge (postmortems and troubleshooting docs). "
        "Returns the top-k most relevant runbook snippets with metadata, source types, and URLs. "
        "Call this tool AFTER inspecting live signals (pod status, logs, metrics) — "
        "use the specific symptoms and error messages you found as the query."
    )
)
def search_runbooks(
    query: str,
    top_k: int = 3,
    include_external: bool = True,
) -> dict:
    """
    Search internal runbooks and curated external postmortems for the given query.

    Args:
        query:            Natural-language description of incident symptoms or errors.
        top_k:            Number of results to return (default 3, max 10).
        include_external: Whether to search external knowledge collection (default True).

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
                    "snippet": str,
                    "source_type": "internal_runbook" | "external_postmortem" | "external_doc",
                    "url": str | null
                }
            ],
            "no_confident_match": bool
        }
    """
    try:
        top_k = max(1, min(int(top_k), 10))

        # 1. Query internal runbooks collection
        internal_chunks = query_runbooks(query, db_path=DEFAULT_DB_PATH, top_k=top_k)
        internal_results = [
            {
                "title": c["title"],
                "source": c["source"],
                "failure_type": c["failure_type"],
                "service": c["service"],
                "score": c["score"],
                "snippet": c["snippet"][:400],
                "source_type": "internal_runbook",
                "url": None,
            }
            for c in internal_chunks
        ]

        # 2. Query external knowledge collection (if enabled)
        external_results = []
        if include_external:
            try:
                external_chunks = query_external_docs(query, db_path=DEFAULT_DB_PATH, top_k=top_k)
                external_results = [
                    {
                        "title": c["title"],
                        "source": c["source"],
                        "failure_type": c["failure_type"],
                        "service": c["service"],
                        "score": c["score"],
                        "snippet": c["snippet"][:400],
                        "source_type": c["source_type"],
                        "url": c.get("url") or None,
                    }
                    for c in external_chunks
                ]
            except Exception:
                # If external knowledge collection is missing, proceed with internal only
                external_results = []

        # 3. Combine and rank:
        # Internal runbooks receive a priority bonus (+0.03) so they win ties and
        # rank above external sources when both match.
        def _sort_key(item: dict) -> float:
            bonus = 0.03 if item["source_type"] == "internal_runbook" else 0.0
            return float(item["score"]) + bonus

        all_candidates = internal_results + external_results
        sorted_candidates = sorted(all_candidates, key=_sort_key, reverse=True)

        # 4. Deduplicate by title to ensure diverse top-k results
        seen_titles: set[str] = set()
        deduped_results: list[dict] = []
        for candidate in sorted_candidates:
            title = candidate["title"]
            if title not in seen_titles:
                seen_titles.add(title)
                deduped_results.append(candidate)
            if len(deduped_results) >= top_k:
                break

        # 5. Determine whether ANY result is above the confidence threshold
        best_score = max((r["score"] for r in deduped_results), default=0.0)
        no_confident_match = best_score < CONFIDENCE_THRESHOLD

        return {
            "query": query,
            "results": deduped_results,
            "no_confident_match": no_confident_match,
        }
    except Exception as exc:
        return {"error": f"search_runbooks failed: {exc}"}


if __name__ == "__main__":
    mcp.run_stdio_async()
