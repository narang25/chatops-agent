#!/usr/bin/env python3
"""
Model Comparison and Benchmarking Script for Amazon Bedrock.

Evaluates 10 candidate models against:
  (a) Hello test (generation + latency)
  (b) Tool-calling test (schema binding + argument passing)
  (c) Reasoning-leak check (ensuring <think> / CoT tokens do not reach user output)

Measures latency per test, catches errors per model so the run continues,
prints a summary comparison table, and writes structured results to:
  agent/scripts/results/model_comparison.json
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from agent.llm import get_llm, clean_output, handle_llm_error, find_and_load_env

# Candidate model IDs specified in task
CANDIDATE_MODELS: List[str] = [
    "qwen.qwen3-next-80b-a3b",
    "qwen.qwen3-vl-235b-a22b",
    "zai.glm-5.3",
    "zai.glm-5",
    "deepseek.v3.2",
    "moonshotai.kimi-k2.5",
    "moonshotai.kimi-k3",
    "minimax.minimax-m2.5",
    "mistral.mistral-large-3-675b-instruct",
    "nvidia.nemotron-super-3-120b",
]


@tool
def get_service_status(service: str) -> Dict[str, Any]:
    """Get the current health, state, and metrics for a given microservice."""
    return {
        "service": service,
        "state": "running",
        "health": "healthy",
        "restart_count": 0,
        "memory_limit_mb": 256,
    }


def evaluate_model(model_id: str) -> Dict[str, Any]:
    """Runs hello, tool-calling, and leak tests for a single model ID."""
    record: Dict[str, Any] = {
        "model_id": model_id,
        "active_model_id": model_id,
        "hello_ok": False,
        "hello_latency": None,
        "hello_reply": "",
        "tool_call_ok": False,
        "tool_call_latency": None,
        "tool_call_detail": "",
        "reasoning_leak": "N/A",
        "avg_latency": None,
        "error_summary": "None",
    }

    try:
        llm = get_llm(model_id=model_id)
        # Capture the active model ID in case fallback updated it
        record["active_model_id"] = getattr(llm, "model_id", model_id)
    except Exception as init_err:
        record["error_summary"] = f"Init error: {type(init_err).__name__}"
        return record

    successful_latencies: List[float] = []

    # 1. Hello Test
    print(f"  -> Testing Hello prompt...")
    try:
        start_time = time.perf_counter()
        response = llm.invoke([HumanMessage(content="Say hello in one sentence.")])
        latency = time.perf_counter() - start_time
        record["hello_latency"] = round(latency, 2)
        successful_latencies.append(latency)

        cleaned_text = clean_output(response)
        record["hello_reply"] = cleaned_text
        record["hello_ok"] = bool(cleaned_text)

        # Update active_model_id if fallback modified it during invoke
        record["active_model_id"] = getattr(llm, "model_id", model_id)

        # 2. Reasoning Leak Check on test 1 reply
        has_think = "<think>" in cleaned_text.lower() or "</think>" in cleaned_text.lower()
        record["reasoning_leak"] = "LEAK" if has_think else "NONE"
        print(f"     ✓ Hello OK ({latency:.2f}s) | Leak: {record['reasoning_leak']}")

    except Exception as e:
        record["hello_ok"] = False
        record["error_summary"] = handle_llm_error(e).split("\n")[0]
        print(f"     ✗ Hello Failed: {record['error_summary']}")

    # 3. Tool Calling Test
    print(f"  -> Testing Tool calling...")
    try:
        start_time = time.perf_counter()
        llm_with_tools = llm.bind_tools([get_service_status])
        tool_prompt = "Is payment-service healthy? Check its status using the tool."
        tool_resp = llm_with_tools.invoke([HumanMessage(content=tool_prompt)])
        tool_latency = time.perf_counter() - start_time
        record["tool_call_latency"] = round(tool_latency, 2)
        successful_latencies.append(tool_latency)

        tool_calls = getattr(tool_resp, "tool_calls", [])
        if not tool_calls and hasattr(tool_resp, "additional_kwargs"):
            tool_calls = tool_resp.additional_kwargs.get("tool_calls", [])

        if tool_calls:
            first_call = tool_calls[0]
            name = first_call.get("name", "")
            args = first_call.get("args", {})
            svc = str(args.get("service", "")).lower()
            if name == "get_service_status" and "payment-service" in svc:
                record["tool_call_ok"] = True
                record["tool_call_detail"] = f"{name}(service='{svc}')"
                print(f"     ✓ Tool Call OK ({tool_latency:.2f}s): {record['tool_call_detail']}")
            else:
                record["tool_call_ok"] = False
                record["tool_call_detail"] = f"Arg mismatch: {name} with {args}"
                print(f"     ✗ Tool Call Arg Mismatch: {record['tool_call_detail']}")
        else:
            record["tool_call_ok"] = False
            record["tool_call_detail"] = "No tool call generated"
            print(f"     ✗ No tool call generated")

    except Exception as e:
        record["tool_call_ok"] = False
        err_short = handle_llm_error(e).split("\n")[0]
        record["tool_call_detail"] = err_short
        if record["error_summary"] == "None":
            record["error_summary"] = err_short
        print(f"     ✗ Tool Call Failed: {err_short}")

    if successful_latencies:
        record["avg_latency"] = round(sum(successful_latencies) / len(successful_latencies), 2)

    return record


def main() -> None:
    find_and_load_env()
    region = os.getenv("AWS_REGION", "us-east-1")

    print("=" * 80)
    print("ChatOps Bedrock Model Comparison Benchmark")
    print(f"Region:          {region}")
    print(f"Candidate count: {len(CANDIDATE_MODELS)}")
    print("=" * 80)

    results: List[Dict[str, Any]] = []

    for idx, model_id in enumerate(CANDIDATE_MODELS, start=1):
        print(f"\n[{idx}/{len(CANDIDATE_MODELS)}] Evaluating model: {model_id}")
        res = evaluate_model(model_id)
        results.append(res)

    # 4. Print Summary Table
    print("\n" + "=" * 105)
    print("MODEL COMPARISON SUMMARY TABLE")
    print("=" * 105)
    header = f"{'Model ID':<36} | {'Hello':<7} | {'Tool Call':<9} | {'Leak':<6} | {'Avg Latency':<11} | {'Error Summary'}"
    print(header)
    print("-" * 105)

    for r in results:
        m_id = r["active_model_id"]
        if len(m_id) > 34:
            m_id = m_id[:31] + "..."
        hello_str = "PASS" if r["hello_ok"] else "FAIL"
        tool_str = "PASS" if r["tool_call_ok"] else "FAIL"
        leak_str = r["reasoning_leak"]
        lat_str = f"{r['avg_latency']}s" if r["avg_latency"] is not None else "N/A"
        err_str = r["error_summary"]
        if len(err_str) > 28:
            err_str = err_str[:25] + "..."

        print(f"{m_id:<36} | {hello_str:<7} | {tool_str:<9} | {leak_str:<6} | {lat_str:<11} | {err_str}")

    print("=" * 105)

    # 5. Save results to JSON
    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / "model_comparison.json"

    payload = {
        "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
        "region": region,
        "total_models_evaluated": len(results),
        "results": results,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\n✓ Detailed results saved to: {json_path}")


if __name__ == "__main__":
    main()
