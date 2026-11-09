"""
ChatOps Agent Benchmark Harness v2 (Week 4 -- Task A18).
=========================================================

Measures agent diagnosis across:
  - 5 Ablation modes:
      1. llm_only          : Raw LLM without tools (measures base model knowledge)
      2. rag_only          : LLM + search_runbooks only (no live tools)
      3. live_tools_only   : LLM + live inspection tools (no runbooks)
      4. full              : Full system (live tools + internal runbooks)
      5. with_external     : Full system + external knowledge (postmortems & docs)
  - 4 Models (Qwen3 VL 235B, Kimi K2.5, DeepSeek V3.2, Mistral Large 3)
  - Trials: 1 to 3 repetitions per scenario
  - Hold-out mode: --hold-out <failure_type> evaluates response when specific runbook is absent
  - Surprise scenarios: --surprise includes unindexed/unseen failure scenarios

Metrics recorded:
  - failure_type_match  : exact match against ground truth (or acceptable types for surprise)
  - fix_keyword_score   : fraction of expected_fix_keywords in recommendation
  - runbook_cited       : whether appropriate runbook/source was cited
  - tool_calls_used     : number of tool calls made
  - latency_s           : wall-clock response latency
  - estimated_cost_usd  : estimated inference cost

Outputs:
  agent/eval/results/<run_id>.json     -- Full structured evaluation records
  agent/eval/results/<run_id>.md       -- Report-ready Markdown tables

Usage:
  python -m agent.eval.benchmark --ablation full --trials 1
  python -m agent.eval.benchmark --ablation all --models all --trials 3
  python -m agent.eval.benchmark --hold-out out_of_memory
  python -m agent.eval.benchmark --surprise
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is in path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent.agent import _make_stub_tools
from agent.api import (
    AGENT_SYSTEM_PROMPT,
    _extract_confidence,
    _extract_failure_type,
    _extract_sources,
)
from agent.eval.scenarios import BENCHMARK_SCENARIOS, SURPRISE_SCENARIOS
from agent.llm import clean_output, get_llm
from mcp_servers.runbooks.server import search_runbooks as _search_runbooks_fn

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_ABLATIONS = [
    "llm_only",
    "rag_only",
    "live_tools_only",
    "full",
    "with_external",
    "multi_agent",
]

DEFAULT_MODELS = [
    "qwen.qwen3-vl-235b-a22b",
    "moonshot.kimi-k2.5",
    "deepseek.deepseek-v3.2",
    "mistral.mistral-large-3",
]

# Estimated cost constants ($ per tool call & second of latency)
COST_PER_TOOL_CALL = 0.0008
COST_PER_LATENCY_SEC = 0.00015


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def score_failure_type(
    predicted: str | None,
    ground_truth: str,
    acceptable_types: list[str] | None = None,
) -> int:
    """1 if exact match or in acceptable_types, else 0."""
    if predicted is None:
        return 0
    pred = predicted.strip().lower()
    gt = ground_truth.strip().lower()
    if pred == gt:
        return 1
    if acceptable_types:
        return int(pred in [t.lower() for t in acceptable_types])
    return 0


def score_fix_keywords(diagnosis: str, keywords: list[str]) -> float:
    """Fraction of expected keywords present in the diagnosis text."""
    if not keywords:
        return 1.0
    text = diagnosis.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text)
    return round(hits / len(keywords), 3)


def score_runbook_cited(
    result: dict,
    keywords: list[str],
    is_unknown: bool = False,
) -> int:
    """
    1 if relevant source cited. If failure is unknown/hold-out,
    cites 1 if agent correctly acknowledges no confident runbook match.
    """
    if is_unknown:
        text = (result.get("diagnosis", "") + " " + " ".join(result.get("sources", []))).lower()
        if "no confident" in text or "no matching runbook" in text or "unknown" in text:
            return 1
        return 0

    combined = " ".join(result.get("sources", [])) + " " + result.get("diagnosis", "")
    for kw in keywords:
        if kw.lower() in combined.lower():
            return 1
    return 0


# ---------------------------------------------------------------------------
# Dynamic Ablation Agent Builder
# ---------------------------------------------------------------------------


def _build_ablation_agent(
    ablation: str = "full",
    model_id: str | None = None,
    hold_out: str | None = None,
    stub: bool = True,
) -> Any:
    """
    Constructs an agent specifically tailored to an ablation configuration:
      - llm_only: pure LLM, no tools
      - rag_only: only search_runbooks tool
      - live_tools_only: status, logs, metrics, events (no search_runbooks)
      - full: live tools + internal runbooks (include_external=False)
      - with_external: live tools + internal runbooks + external postmortems
    """
    llm = get_llm(model_id=model_id)

    if ablation == "llm_only":
        # Pure LLM with system prompt and no tool wrappers
        return create_react_agent(
            model=llm,
            tools=[],
            prompt=AGENT_SYSTEM_PROMPT,
        )

    # Search runbooks tool wrapper respecting hold_out and ablation flags
    include_ext = (ablation == "with_external")

    @tool
    def search_runbooks(query: str, top_k: int = 3) -> str:
        """Search SRE runbooks knowledge base."""
        res = _search_runbooks_fn(query=query, top_k=top_k, include_external=include_ext)
        if hold_out and isinstance(res, dict) and "results" in res:
            # Filter out hold-out failure type from search results
            filtered = [
                r for r in res["results"]
                if r.get("failure_type", "").lower() != hold_out.lower()
            ]
            res["results"] = filtered
            res["no_confident_match"] = (
                len(filtered) == 0 or max((r.get("score", 0.0) for r in filtered), default=0.0) < 0.60
            )
        return json.dumps(res, indent=2)

    tools = []
    if ablation in ("full", "with_external", "live_tools_only"):
        tools.extend(_make_stub_tools())

    if ablation in ("full", "with_external", "rag_only"):
        tools.append(search_runbooks)

    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=AGENT_SYSTEM_PROMPT,
    )


def execute_ablation_ask(
    question: str,
    ablation: str = "full",
    model_id: str | None = None,
    hold_out: str | None = None,
    stub: bool = True,
) -> dict[str, Any]:
    """Executes a diagnostic query under a given ablation configuration."""
    if ablation == "multi_agent":
        from agent.multi.sub_agents import multi_agent_ask
        return multi_agent_ask(
            question=question,
            model_id=model_id,
            stub=stub,
        )

    agent = _build_ablation_agent(
        ablation=ablation,
        model_id=model_id,
        hold_out=hold_out,
        stub=stub,
    )
    t0 = time.perf_counter()
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    latency = round(time.perf_counter() - t0, 3)

    messages = result.get("messages", [])
    final_msg = messages[-1] if messages else None
    diagnosis = clean_output(final_msg) if final_msg else ""

    tool_trace = []
    for msg in messages:
        if getattr(msg, "type", None) == "tool":
            name = getattr(msg, "name", "unknown_tool")
            content = str(getattr(msg, "content", ""))
            summary = (content[:120] + "...") if len(content) > 120 else content
            tool_trace.append({"tool": name, "output_summary": summary})

    return {
        "question": question,
        "diagnosis": diagnosis,
        "failure_type": _extract_failure_type(diagnosis),
        "confidence": _extract_confidence(diagnosis),
        "tool_trace": tool_trace,
        "sources": _extract_sources(diagnosis),
        "latency_s": latency,
        "model_id": model_id,
        "ablation": ablation,
    }


# ---------------------------------------------------------------------------
# Single Scenario Evaluator
# ---------------------------------------------------------------------------


def evaluate_scenario(
    scenario: dict,
    ablation: str = "full",
    model_id: str | None = None,
    hold_out: str | None = None,
    trial: int = 1,
) -> dict:
    """Runs a single benchmark scenario and scores output."""
    sid = scenario["scenario_id"]
    service = scenario["service"]
    question = scenario["question"]
    ground_truth_ft = scenario["failure_type"]
    acceptable_fts = scenario.get("acceptable_failure_types")
    is_surprise = sid.startswith("surprise-") or (hold_out and ground_truth_ft == hold_out)

    display_model = (model_id or "default").split("/")[-1]
    print(f"  [{ablation:15s} | {display_model:18s} | T{trial}] {sid:<24} ...", end=" ", flush=True)

    try:
        res = execute_ablation_ask(
            question=question,
            ablation=ablation,
            model_id=model_id,
            hold_out=hold_out,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return {
            "scenario_id": sid,
            "service": service,
            "ablation": ablation,
            "model_id": model_id,
            "trial": trial,
            "hold_out": hold_out,
            "failure_type_match": 0,
            "fix_keyword_score": 0.0,
            "runbook_cited": 0,
            "tool_calls_used": 0,
            "latency_s": -1.0,
            "estimated_cost_usd": 0.0,
            "predicted_failure_type": None,
            "ground_truth_failure_type": ground_truth_ft,
            "error": str(exc),
        }

    ft_match = score_failure_type(res.get("failure_type"), ground_truth_ft, acceptable_fts)
    fix_score = score_fix_keywords(res.get("diagnosis", ""), scenario.get("expected_fix_keywords", []))
    rb_cited = score_runbook_cited(res, scenario.get("expected_runbook_keywords", []), is_unknown=is_surprise)
    num_tools = len(res.get("tool_trace", []))
    lat = res.get("latency_s", -1.0)
    cost = round((num_tools * COST_PER_TOOL_CALL) + (max(0.0, lat) * COST_PER_LATENCY_SEC), 5)

    print(f"FT={'PASS' if ft_match else 'FAIL':4s} Fix={fix_score:.2f} RB={'Y' if rb_cited else 'N'} Tools={num_tools:2d} Lat={lat:.1f}s Cost=${cost:.4f}")

    return {
        "scenario_id": sid,
        "service": service,
        "ablation": ablation,
        "model_id": model_id,
        "trial": trial,
        "hold_out": hold_out,
        "failure_type_match": ft_match,
        "fix_keyword_score": fix_score,
        "runbook_cited": rb_cited,
        "tool_calls_used": num_tools,
        "latency_s": lat,
        "estimated_cost_usd": cost,
        "predicted_failure_type": res.get("failure_type"),
        "ground_truth_failure_type": ground_truth_ft,
        "confidence": res.get("confidence"),
        "error": None,
    }


# ---------------------------------------------------------------------------
# Aggregation & Report Generation
# ---------------------------------------------------------------------------


def generate_benchmark_report(
    run_id: str,
    records: list[dict],
    ablations_run: list[str],
    models_run: list[str | None],
    hold_out: str | None = None,
) -> tuple[Path, Path]:
    """Generates JSON and Markdown summary tables for the benchmark."""
    json_path = RESULTS_DIR / f"{run_id}.json"
    md_path = RESULTS_DIR / f"{run_id}.md"

    # Write JSON record dump
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ablations": ablations_run,
            "models": [m or "default" for m in models_run],
            "hold_out": hold_out,
            "total_evaluations": len(records),
            "records": records,
        }, f, indent=2)

    # Compute aggregation by (ablation, model)
    summary_rows = []
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in records:
        key = (r["ablation"], r["model_id"] or "default")
        groups.setdefault(key, []).append(r)

    for (abl, mdl), grp in groups.items():
        n = len(grp)
        ft_acc = round(sum(r["failure_type_match"] for r in grp) / n * 100, 1)
        fix_acc = round(sum(r["fix_keyword_score"] for r in grp) / n * 100, 1)
        rb_cite = round(sum(r["runbook_cited"] for r in grp) / n * 100, 1)
        avg_tools = round(sum(r["tool_calls_used"] for r in grp) / n, 2)
        valid_lats = [r["latency_s"] for r in grp if r["latency_s"] >= 0]
        avg_lat = round(sum(valid_lats) / max(1, len(valid_lats)), 2)
        avg_cost = round(sum(r["estimated_cost_usd"] for r in grp) / n, 4)

        summary_rows.append({
            "ablation": abl,
            "model": mdl.split("/")[-1],
            "samples": n,
            "ft_accuracy_pct": ft_acc,
            "fix_quality_pct": fix_acc,
            "citation_rate_pct": rb_cite,
            "avg_tools": avg_tools,
            "avg_latency_s": avg_lat,
            "avg_cost_usd": avg_cost,
        })

    model_labels = ", ".join(f"`{m or 'default'}`" for m in models_run)
    ablation_labels = ", ".join(f"`{a}`" for a in ablations_run)
    hold_out_label = hold_out or "None"

    # Render Markdown
    md_lines = [
        f"# ChatOps Agent Benchmark Report — `{run_id}`",
        "",
        f"- **Timestamp**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **Ablations Evaluated**: {ablation_labels}",
        f"- **Models**: {model_labels}",
        f"- **Hold-Out Setting**: `{hold_out_label}`",
        f"- **Total Evaluations**: `{len(records)}`",
        "",
        "## Summary Results",
        "",
        "| Configuration | Model | FT Accuracy | Fix Quality | Citation Rate | Avg Tools | Avg Latency | Est Cost / Incident |",
        "|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for row in summary_rows:
        md_lines.append(
            f"| `{row['ablation']}` | `{row['model']}` | "
            f"**{row['ft_accuracy_pct']}%** | {row['fix_quality_pct']}% | {row['citation_rate_pct']}% | "
            f"{row['avg_tools']} | {row['avg_latency_s']}s | ${row['avg_cost_usd']} |"
        )

    md_lines.extend([
        "",
        "## Evaluation Details",
        "",
        "| Scenario | Ablation | Model | Trial | FT Match | Fix Score | RB Cited | Tools | Latency |",
        "|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ])

    for r in records:
        md_lines.append(
            f"| `{r['scenario_id']}` | `{r['ablation']}` | `{str(r['model_id'] or 'default').split('/')[-1]}` | "
            f"{r['trial']} | {'✅' if r['failure_type_match'] else '❌'} | {r['fix_keyword_score']:.2f} | "
            f"{'✅' if r['runbook_cited'] else '❌'} | {r['tool_calls_used']} | {r['latency_s']:.1f}s |"
        )

    md_lines.extend(["", "---", "_Generated automatically by ChatOps Benchmark Harness v2_"])
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return json_path, md_path


# ---------------------------------------------------------------------------
# Runner Entry Point
# ---------------------------------------------------------------------------


def run_benchmark(
    ablations: list[str],
    models: list[str | None],
    trials: int = 1,
    include_surprise: bool = False,
    hold_out: str | None = None,
) -> tuple[Path, Path]:
    """Runs full benchmark matrix across selected ablations, models, and trials."""
    scenarios = list(BENCHMARK_SCENARIOS)
    if include_surprise:
        scenarios.extend(SURPRISE_SCENARIOS)

    run_id = f"bm_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if hold_out:
        run_id += f"_holdout_{hold_out}"

    print(f"\n{'='*75}")
    print(f"  ChatOps SRE Agent Benchmark v2  [{run_id}]")
    print(f"  Scenarios: {len(scenarios)} | Ablations: {len(ablations)} | Models: {len(models)} | Trials: {trials}")
    if hold_out:
        print(f"  Hold-Out Mode: Runbook '{hold_out}' EXCLUDED from retrieval")
    print(f"{'='*75}\n")

    records: list[dict] = []
    for abl in ablations:
        for mdl in models:
            for trial in range(1, trials + 1):
                for sc in scenarios:
                    rec = evaluate_scenario(
                        scenario=sc,
                        ablation=abl,
                        model_id=mdl,
                        hold_out=hold_out,
                        trial=trial,
                    )
                    records.append(rec)

    json_p, md_p = generate_benchmark_report(
        run_id=run_id,
        records=records,
        ablations_run=ablations,
        models_run=models,
        hold_out=hold_out,
    )

    print(f"\n{'='*75}")
    print("  Benchmark Complete! Results saved to:")
    print(f"    Markdown: {md_p}")
    print(f"    JSON:     {json_p}")
    print(f"{'='*75}\n")

    return json_p, md_p


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChatOps Benchmark Harness v2")
    parser.add_argument(
        "--ablation",
        type=str,
        default="full",
        help="Ablation mode: llm_only | rag_only | live_tools_only | full | with_external | all",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="default",
        help="Models: 'default', 'all', or specific comma-separated model IDs",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=1,
        help="Number of trials per scenario (default: 1)",
    )
    parser.add_argument(
        "--surprise",
        action="store_true",
        help="Include surprise unseen failure scenarios",
    )
    parser.add_argument(
        "--hold-out",
        type=str,
        default=None,
        help="Failure type to hold out (exclude from runbook search)",
    )

    args = parser.parse_args()

    # Determine ablations
    if args.ablation == "all":
        ablations_to_run = SUPPORTED_ABLATIONS
    else:
        ablations_to_run = [a.strip() for a in args.ablation.split(",") if a.strip()]

    # Determine models
    if args.models == "all":
        models_to_run: list[str | None] = [None] + DEFAULT_MODELS  # None uses default configured model
    elif args.models == "default":
        models_to_run = [None]
    else:
        models_to_run = [m.strip() for m in args.models.split(",") if m.strip()]

    run_benchmark(
        ablations=ablations_to_run,
        models=models_to_run,
        trials=args.trials,
        include_surprise=args.surprise,
        hold_out=args.hold_out,
    )
