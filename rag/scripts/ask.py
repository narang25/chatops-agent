#!/usr/bin/env python3
"""
CLI Query Script for RAG Runbook Assistant.

Usage:
  python rag/scripts/ask.py "why is payment-service restarting with exit code 137?"
  python rag/scripts/ask.py "order-service failed to start" --top-k 5
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.llm import handle_llm_error, load_config
from rag.chain import RAGChain


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask questions about incidents and retrieve grounded runbook fixes.")
    parser.add_argument("question", type=str, help="Incident question or error message")
    parser.add_argument("--top-k", type=int, default=3, help="Number of runbook chunks to retrieve (default: 3)")
    parser.add_argument("--model-id", type=str, default=None, help="Override LLM model ID")

    args = parser.parse_args()

    config = load_config()
    provider = config.get("provider", "bedrock")
    model_name = args.model_id or (config.get("bedrock", {}).get("model_id") if provider == "bedrock" else config.get("ollama", {}).get("model"))

    print("=" * 80)
    print(f"ChatOps Incident Diagnostic Assistant (Provider: {provider} | Model: {model_name})")
    print("=" * 80)
    print(f"Question: \"{args.question}\"\n")

    try:
        chain = RAGChain(top_k=args.top_k, model_id=args.model_id)

        start_time = time.perf_counter()
        result = chain.run(args.question)
        elapsed = time.perf_counter() - start_time

        print("DIAGNOSIS & SUGGESTED FIX:")
        print("-" * 80)
        print(result["answer"])
        print("-" * 80)

        print("\nCITED SOURCES:")
        for idx, src in enumerate(result["sources"], start=1):
            print(f"  [{idx}] {src['title']} ({src['source']} > Section: {src['section']}) [Score: {src['score']}]")

        print(f"\nLatency: {elapsed:.2f}s | Chunks Retrieved: {len(result['retrieved_chunks'])}")
        print("=" * 80)

    except Exception as e:
        print("✗ Error running RAG chain:")
        print(handle_llm_error(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
