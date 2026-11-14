#!/usr/bin/env python3
"""
Direct Runbook Search CLI.
=========================

Usage:
    python rag/search.py "<query>" [--top-k N]

Example:
    python rag/search.py "container killed exit code 137 out of memory"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.runbooks.server import search_runbooks


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the runbook knowledge base directly.")
    parser.add_argument("query", type=str, help="Search query (e.g. 'container killed out of memory')")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of results to return (default: 3)")
    args = parser.parse_args()

    # Manual search directly inspects RAG without agent evidence gate
    res = search_runbooks(query=args.query, top_k=args.top_k, enforce_evidence=False)

    if "error" in res:
        print(f"Error: {res['error']}", file=sys.stderr)
        sys.exit(1)

    results = res.get("results", [])
    no_confident = res.get("no_confident_match", False)

    print("\n" + "=" * 70)
    print(f"Search Results for: '{args.query}' (top {len(results)})")
    if no_confident:
        print("Note: [no_confident_match: True] — all scores below confidence threshold (0.60)")
    print("=" * 70)

    if not results:
        print("No matching runbooks found.")
        return

    for i, r in enumerate(results, start=1):
        url_line = f"URL:          {r['url']}\n" if r.get("url") else ""
        print(f"\n#{i} Title:        {r.get('title')}")
        print(f"   Source Type:  {r.get('source_type')}")
        print(f"   Failure Type: {r.get('failure_type')}")
        print(f"   Service:      {r.get('service')}")
        print(f"   Score:        {r.get('score')}")
        if url_line:
            print(f"   {url_line.strip()}")
        print(f"   Source File:  {r.get('source')}")
        print(f"   Snippet:\n     {r.get('snippet', '')[:250]}...")

    print("\n" + "-" * 70 + "\n")


if __name__ == "__main__":
    main()
