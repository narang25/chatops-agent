#!/usr/bin/env python3
"""
RAG Retrieval Evaluation Script (Task A4).

Evaluates the Chroma vector retriever on the 10 benchmark questions
defined in rag/eval/questions.yaml. Computes:
- Hit Rate @ Top-1
- Hit Rate @ Top-3
- Mean Reciprocal Rank (MRR)
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.ingest import query_runbooks


def evaluate_retrieval(eval_file: Path) -> Dict[str, Any]:
    with open(eval_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    questions = data.get("questions", [])
    if not questions:
        raise ValueError(f"No questions found in {eval_file}")

    print("=" * 95)
    print("ChatOps RAG Retrieval Evaluation (Hit Rate @ 1 & Hit Rate @ 3)")
    print(f"Dataset:         {eval_file}")
    print(f"Total questions: {len(questions)}")
    print("=" * 95)

    hits_at_1 = 0
    hits_at_3 = 0
    reciprocal_ranks: List[float] = []
    eval_records: List[Dict[str, Any]] = []

    print(f"{'ID':<3} | {'Expected Runbook':<32} | {'Top Match':<32} | {'Rank':<5} | {'H@1':<4} | {'H@3'}")
    print("-" * 95)

    for item in questions:
        q_id = item.get("id")
        q_text = item.get("question")
        expected = item.get("expected_runbook")

        # Query vector store for top 3
        results = query_runbooks(q_text, top_k=3)

        retrieved_sources = [Path(r["source"]).name for r in results]
        rank = -1
        for idx, src in enumerate(retrieved_sources, start=1):
            if expected in src or src in expected:
                rank = idx
                break

        is_hit_1 = (rank == 1)
        is_hit_3 = (1 <= rank <= 3)

        if is_hit_1:
            hits_at_1 += 1
        if is_hit_3:
            hits_at_3 += 1

        rr = (1.0 / rank) if rank > 0 else 0.0
        reciprocal_ranks.append(rr)

        top_match = retrieved_sources[0] if retrieved_sources else "None"
        rank_str = f"#{rank}" if rank > 0 else "-"

        print(
            f"{q_id:<3} | {expected:<32} | {top_match:<32} | {rank_str:<5} | "
            f"{'✓' if is_hit_1 else '✗':<4} | {'✓' if is_hit_3 else '✗'}"
        )

        eval_records.append({
            "id": q_id,
            "question": q_text,
            "expected_runbook": expected,
            "top_match": top_match,
            "retrieved_sources": retrieved_sources,
            "rank": rank,
            "hit_at_1": is_hit_1,
            "hit_at_3": is_hit_3,
            "reciprocal_rank": rr,
        })

    total = len(questions)
    hr_1 = (hits_at_1 / total) * 100.0
    hr_3 = (hits_at_3 / total) * 100.0
    mrr = sum(reciprocal_ranks) / total if total > 0 else 0.0

    print("=" * 95)
    print("EVALUATION METRICS SUMMARY")
    print("=" * 95)
    print(f"Total Evaluated Questions: {total}")
    print(f"Hit Rate @ Top-1:          {hr_1:.1f}% ({hits_at_1}/{total})")
    print(f"Hit Rate @ Top-3:          {hr_3:.1f}% ({hits_at_3}/{total})")
    print(f"Mean Reciprocal Rank (MRR): {mrr:.3f}")
    print("=" * 95)

    results_payload = {
        "evaluation_timestamp": time.time(),
        "total_questions": total,
        "hit_rate_at_1": hr_1,
        "hit_rate_at_3": hr_3,
        "mean_reciprocal_rank": mrr,
        "records": eval_records,
    }

    out_json = eval_file.parent / "results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    print(f"Detailed evaluation saved to: {out_json}")
    return results_payload


def main() -> None:
    eval_file = PROJECT_ROOT / "rag" / "eval" / "questions.yaml"
    if not eval_file.exists():
        print(f"Error: Evaluation dataset not found at {eval_file}")
        sys.exit(1)

    evaluate_retrieval(eval_file)


if __name__ == "__main__":
    main()
