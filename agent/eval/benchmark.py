"""
ChatOps Agent Benchmark Harness  (Week 3 -- Task A11)
======================================================

Runs the agent against all BENCHMARK_SCENARIOS and measures:
  - failure_type_match  : exact match of extracted failure type vs ground truth
  - fix_keyword_match   : fraction of expected_fix_keywords present in diagnosis
  - runbook_cited       : whether a relevant runbook keyword appears in sources
  - tool_calls_used     : number of tool calls made
  - latency_s           : wall-clock time for the agent response

Ablation modes
--------------
  full     : agent with all 4 tools (search_runbooks + 3 live-tool stubs)
  rag_only : agent with only search_runbooks (no live metrics/events/pod status)

Results are written to:
  agent/eval/results/<run_id>.json     -- full structured results
  agent/eval/results/<run_id>.md       -- human-readable markdown table

Usage
-----
    python -m agent.eval.benchmark [--ablation full|rag_only] [--trials N]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path when run as a module
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent.eval.scenarios import BENCHMARK_SCENARIOS
from agent.api import ask

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def score_failure_type(predicted: str | None, ground_truth: str) -> int:
    """1 if exact match (case-insensitive), else 0."""
    if predicted is None:
        return 0
    return int(predicted.strip().lower() == ground_truth.strip().lower())


def score_fix_keywords(diagnosis: str, keywords: list[str]) -> float:
    """Fraction of expected keywords found in the diagnosis text."""
    if not keywords:
        return 1.0
    hits = sum(1 for kw in keywords if kw.lower() in diagnosis.lower())
    return round(hits / len(keywords), 3)


def score_runbook_cited(result: dict, keywords: list[str]) -> int:
    """1 if any expected runbook keyword appears in sources or diagnosis."""
    combined = " ".join(result.get("sources", [])) + " " + result.get("diagnosis", "")
    for kw in keywords:
        if kw.lower() in combined.lower():
            return 1
    return 0


# ---------------------------------------------------------------------------
# RAG-only agent builder (only search_runbooks tool)
# ---------------------------------------------------------------------------


def _build_rag_only_agent():
    """Build an agent with only the runbook search tool for ablation testing."""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.prebuilt import create_react_agent
    from agent.llm import get_llm
    from agent.api import search_runbooks, AGENT_SYSTEM_PROMPT

    llm = get_llm()
    return create_react_agent(
        model=llm,
        tools=[search_runbooks],
        prompt=AGENT_SYSTEM_PROMPT,
        checkpointer=MemorySaver(),
    )


def ask_rag_only(question: str) -> dict:
    """Run the rag-only ablation agent and return a result dict."""
    from agent.llm import clean_output
    import time

    agent = _build_rag_only_agent()
    t0 = time.perf_counter()
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    latency = round(time.perf_counter() - t0, 3)

    messages = result.get("messages", [])
    final_msg = messages[-1] if messages else None
    diagnosis = clean_output(final_msg) if final_msg else ""

    # Reuse extractors from api module
    from agent.api import (
        _extract_failure_type,
        _extract_confidence,
        _extract_sources,
        _build_tool_trace,
    )

    return {
        "question": question,
        "diagnosis": diagnosis,
        "failure_type": _extract_failure_type(diagnosis),
        "confidence": _extract_confidence(diagnosis),
        "tool_trace": _build_tool_trace(messages),
        "sources": _extract_sources(diagnosis),
        "latency_s": latency,
        "thread_id": None,
        "model_id": None,
    }


# ---------------------------------------------------------------------------
# Single scenario runner
# ---------------------------------------------------------------------------


def run_scenario(scenario: dict, ablation: str = "full", trial: int = 1) -> dict:
    """Run a single scenario and return a structured result record."""
    question = scenario["question"]
    service = scenario["service"]
    ground_truth_ft = scenario["failure_type"]

    print(
        f"  [Trial {trial}] {scenario['scenario_id']} ({ablation}) ...",
        end=" ",
        flush=True,
    )

    try:
        if ablation == "rag_only":
            result = ask_rag_only(question)
        else:
            result = ask(question)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return {
            "scenario_id": scenario["scenario_id"],
            "service": service,
            "trial": trial,
            "ablation": ablation,
            "failure_type_match": 0,
            "fix_keyword_score": 0.0,
            "runbook_cited": 0,
            "tool_calls_used": 0,
            "latency_s": -1,
            "predicted_failure_type": None,
            "ground_truth_failure_type": ground_truth_ft,
            "confidence": None,
            "error": str(exc),
        }

    ft_match = score_failure_type(result.get("failure_type"), ground_truth_ft)
    fix_score = score_fix_keywords(
        result.get("diagnosis", ""), scenario.get("expected_fix_keywords", [])
    )
    rb_cited = score_runbook_cited(result, scenario.get("expected_runbook_keywords", []))
    tool_calls = len(result.get("tool_trace", []))
    latency = result.get("latency_s", -1)

    print(
        f"ft={'PASS' if ft_match else 'FAIL'} "
        f"fix={fix_score:.2f} rb={'Y' if rb_cited else 'N'} "
        f"tools={tool_calls} lat={latency}s"
    )

    return {
        "scenario_id": scenario["scenario_id"],
        "service": service,
        "trial": trial,
        "ablation": ablation,
        "failure_type_match": ft_match,
        "fix_keyword_score": fix_score,
        "runbook_cited": rb_cited,
        "tool_calls_used": tool_calls,
        "latency_s": latency,
        "predicted_failure_type": result.get("failure_type"),
        "ground_truth_failure_type": ground_truth_ft,
        "confidence": result.get("confidence"),
        "error": None,
    }


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def _summarise(records: list[dict]) -> dict:
    """Aggregate statistics across all records."""
    if not records:
        return {}
    n = len(records)
    return {
        "total_scenarios": n,
        "failure_type_accuracy": round(sum(r["failure_type_match"] for r in records) / n, 3),
        "avg_fix_keyword_score": round(sum(r["fix_keyword_score"] for r in records) / n, 3),
        "runbook_citation_rate": round(sum(r["runbook_cited"] for r in records) / n, 3),
        "avg_tool_calls": round(sum(r["tool_calls_used"] for r in records) / n, 2),
        "avg_latency_s": round(sum(r["latency_s"] for r in records if r["latency_s"] >= 0) / max(1, sum(1 for r in records if r["latency_s"] >= 0)), 3),
    }


def _write_markdown(run_id: str, records: list[dict], summary_full: dict, summary_rag: dict) -> Path:
    """Write a human-readable markdown benchmark report."""
    md_path = RESULTS_DIR / f"{run_id}.md"
    lines = [
        f"# ChatOps Agent Benchmark — {run_id}",
        "",
        f"**Run timestamp**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Scenarios**: {len(BENCHMARK_SCENARIOS)}  |  **Total records**: {len(records)}",
        "",
        "## Summary",
        "",
        "| Metric | Full Agent | RAG Only |",
        "|--------|-----------|---------|",
    ]
    metrics = [
        ("Failure Type Accuracy", "failure_type_accuracy"),
        ("Avg Fix Keyword Score", "avg_fix_keyword_score"),
        ("Runbook Citation Rate", "runbook_citation_rate"),
        ("Avg Tool Calls", "avg_tool_calls"),
        ("Avg Latency (s)", "avg_latency_s"),
    ]
    for label, key in metrics:
        full_val = summary_full.get(key, "N/A")
        rag_val = summary_rag.get(key, "N/A")
        lines.append(f"| {label} | {full_val} | {rag_val} |")

    lines += [
        "",
        "## Detailed Results",
        "",
        "| Scenario | Ablation | Trial | FT Match | Fix Score | RB Cited | Tools | Latency(s) | Predicted FT |",
        "|----------|----------|-------|----------|-----------|----------|-------|-----------|--------------|",
    ]
    for r in records:
        lines.append(
            f"| {r['scenario_id']} | {r['ablation']} | {r['trial']} "
            f"| {'✅' if r['failure_type_match'] else '❌'} "
            f"| {r['fix_keyword_score']:.2f} "
            f"| {'✅' if r['runbook_cited'] else '❌'} "
            f"| {r['tool_calls_used']} "
            f"| {r['latency_s']} "
            f"| {r.get('predicted_failure_type', '?')} |"
        )

    lines += ["", "---", "_Auto-generated by `agent/eval/benchmark.py`_"]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(ablation: str = "full", trials: int = 1) -> None:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + f"_{ablation}"
    print(f"\n{'='*60}")
    print(f" ChatOps Agent Benchmark  |  ablation={ablation}  trials={trials}")
    print(f" run_id: {run_id}")
    print(f"{'='*60}\n")

    all_records: list[dict] = []
    ablations = ["full", "rag_only"] if ablation == "both" else [ablation]

    for ab in ablations:
        print(f"\n--- Ablation: {ab} ---")
        for scenario in BENCHMARK_SCENARIOS:
            print(f"\nScenario: {scenario['scenario_id']}")
            for trial in range(1, trials + 1):
                rec = run_scenario(scenario, ablation=ab, trial=trial)
                all_records.append(rec)

    # Separate records by ablation
    full_records = [r for r in all_records if r["ablation"] == "full"]
    rag_records = [r for r in all_records if r["ablation"] == "rag_only"]

    summary_full = _summarise(full_records)
    summary_rag = _summarise(rag_records)

    # Persist JSON
    json_path = RESULTS_DIR / f"{run_id}.json"
    json_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "summary_full": summary_full,
                "summary_rag_only": summary_rag,
                "records": all_records,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Persist Markdown
    md_path = _write_markdown(run_id, all_records, summary_full, summary_rag)

    print(f"\n{'='*60}")
    print(f" Results saved:")
    print(f"   JSON: {json_path}")
    print(f"   MD:   {md_path}")
    print(f"\n FULL AGENT SUMMARY:")
    for k, v in summary_full.items():
        print(f"   {k}: {v}")
    if summary_rag:
        print(f"\n RAG-ONLY SUMMARY:")
        for k, v in summary_rag.items():
            print(f"   {k}: {v}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChatOps Agent Benchmark")
    parser.add_argument(
        "--ablation",
        choices=["full", "rag_only", "both"],
        default="full",
        help="Which ablation mode to run (default: full)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=1,
        help="Number of trials per scenario (default: 1)",
    )
    args = parser.parse_args()
    main(ablation=args.ablation, trials=args.trials)
