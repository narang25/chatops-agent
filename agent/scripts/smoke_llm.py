#!/usr/bin/env python3
"""
Smoke Test Suite for ChatOps Agent LLM Connection.

Runs three verification tests:
1. Hello Test: sends "Say hello in one sentence." and prints cleaned reply + latency.
2. Tool-Calling Test: binds a dummy get_service_status tool, queries health of payment-service,
   and verifies that the model generates a tool call with correct arguments.
3. Reasoning-Leak Test: asserts that cleaned replies never leak <think> tags or reasoning blocks.

Supports both Bedrock and Ollama seamlessly by updating agent/config.yaml.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from agent.llm import get_llm, clean_output, load_config, handle_llm_error


# Define dummy tool for test 2
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


def test_hello(llm: Any) -> tuple[bool, str, float]:
    """Test A: Basic hello prompt."""
    prompt = "Say hello in one sentence."
    start_time = time.perf_counter()
    response = llm.invoke([HumanMessage(content=prompt)])
    latency = time.perf_counter() - start_time

    cleaned_reply = clean_output(response)
    success = bool(cleaned_reply)
    return success, cleaned_reply, latency


def test_tool_calling(llm: Any) -> tuple[bool, str, float]:
    """Test B: Tool calling capability with a dummy service status tool."""
    start_time = time.perf_counter()
    try:
        llm_with_tools = llm.bind_tools([get_service_status])
        prompt = "Is payment-service healthy? Check its status using the tool."
        response = llm_with_tools.invoke([HumanMessage(content=prompt)])
        latency = time.perf_counter() - start_time

        # Inspect tool calls
        tool_calls = getattr(response, "tool_calls", [])
        if not tool_calls and hasattr(response, "additional_kwargs"):
            # Check converse API raw blocks if tool calls are located there
            tool_calls = response.additional_kwargs.get("tool_calls", [])

        if not tool_calls:
            detail = f"FAIL - Model did not generate a tool call. Response: {response.content}"
            return False, detail, latency

        # Check the first tool call
        call = tool_calls[0]
        tool_name = call.get("name", "")
        args = call.get("args", {})
        service_arg = args.get("service", "")

        is_match = (
            tool_name == "get_service_status"
            and "payment-service" in str(service_arg).lower()
        )

        if is_match:
            detail = f"PASS - Tool called: {tool_name}(service='{service_arg}')"
            return True, detail, latency
        else:
            detail = (
                f"FAIL - Tool call arguments mismatch. "
                f"Called '{tool_name}' with args {args}"
            )
            return False, detail, latency

    except Exception as e:
        latency = time.perf_counter() - start_time
        raise e


def test_reasoning_leak(sample_reply: str) -> tuple[bool, str, float]:
    """Test C: Reasoning leak assertion on cleaned text."""
    start_time = time.perf_counter()

    # 1. Verify against sample reply from live model
    has_think_open = "<think>" in sample_reply.lower()
    has_think_close = "</think>" in sample_reply.lower()

    # 2. Synthetic verification of the sanitization function
    raw_synthetic = "<think>Secret CoT reasoning\nMulti-step thinking</think>Visible final answer."
    cleaned_synthetic = clean_output(raw_synthetic)
    synthetic_ok = (cleaned_synthetic == "Visible final answer.")

    latency = time.perf_counter() - start_time

    if not has_think_open and not has_think_close and synthetic_ok:
        detail = "PASS - No <think> tags or raw reasoning leaked into cleaned output."
        return True, detail, latency
    else:
        detail = f"FAIL - Leak detected! has_think={has_think_open or has_think_close}, synthetic_ok={synthetic_ok}"
        return False, detail, latency


def main() -> None:
    print("=" * 70)
    print("ChatOps Agent LLM Smoke Test Suite")
    print("=" * 70)

    # 1. Load config
    config = load_config()
    provider = config.get("provider", "bedrock")
    print(f"Provider:    {provider}")
    if provider == "bedrock":
        print(f"Model ID:    {config.get('bedrock', {}).get('model_id')}")
        print(f"Region:      {config.get('bedrock', {}).get('region')}")
    else:
        print(f"Model:       {config.get('ollama', {}).get('model')}")
        print(f"Base URL:    {config.get('ollama', {}).get('base_url')}")
    print("=" * 70)

    # 2. Initialize LLM
    try:
        llm = get_llm()
        print("✓ LLM client initialized successfully.\n")
    except Exception as e:
        print("✗ Failed to initialize LLM client:")
        print(handle_llm_error(e))
        sys.exit(1)

    hello_reply = ""

    # Test 1: Hello Test
    print("[1/3] Running Hello Test...")
    try:
        ok, reply, latency = test_hello(llm)
        hello_reply = reply
        print(f"  Latency: {latency:.2f}s")
        print(f"  Reply:   \"{reply}\"")
        print(f"  Result:  {'PASS' if ok else 'FAIL'}\n")
    except Exception as e:
        print("  Result:  FAIL")
        print("  Error:   " + handle_llm_error(e) + "\n")

    # Test 2: Tool-Calling Test
    print("[2/3] Running Tool-Calling Test...")
    try:
        ok, detail, latency = test_tool_calling(llm)
        print(f"  Latency: {latency:.2f}s")
        print(f"  Detail:  {detail}")
        print(f"  Result:  {'PASS' if ok else 'FAIL'}\n")
    except Exception as e:
        print("  Result:  FAIL")
        print("  Error:   " + handle_llm_error(e) + "\n")

    # Test 3: Reasoning-Leak Test
    print("[3/3] Running Reasoning-Leak Test...")
    ok, detail, latency = test_reasoning_leak(hello_reply)
    print(f"  Latency: {latency:.4f}s")
    print(f"  Detail:  {detail}")
    print(f"  Result:  {'PASS' if ok else 'FAIL'}\n")

    print("=" * 70)
    print("Smoke test execution finished.")
    print("=" * 70)


if __name__ == "__main__":
    main()
