"""
Parallel Multi-Agent Architecture (Week 4 -- Task A19).
========================================================

Decomposes microservice incident diagnosis into three concurrent specialist
sub-agents, each focused on one telemetry domain:

  1. LogAgent      -- Analyzes error logs, stack traces, and unhandled exceptions
  2. MetricsAgent  -- Analyzes Prometheus numeric metrics (CPU, memory, latency, errors)
  3. EventsAgent   -- Analyzes container lifecycle events, restarts, and OOM kills

Concurrent Execution:
  The three specialists run simultaneously via `asyncio.gather()`, reducing
  wall-clock time compared to sequential execution.

CoordinatorAgent:
  Synthesizes pre-analyzed reports from all three specialists, validates symptoms
  against SRE runbooks via `search_runbooks`, and outputs a ranked, evidence-backed
  incident diagnosis with confidence scoring.

Usage:
  from agent.multi.sub_agents import multi_agent_ask
  result = multi_agent_ask("Why did payment-service fail?")
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent.api import (
    _build_tool_trace,
    _extract_confidence,
    _extract_failure_type,
    _extract_sources,
)
from agent.llm import clean_output, get_llm
from agent.stub_tools import (
    stub_get_events,
    stub_get_logs,
    stub_get_metrics,
    stub_get_pod_status,
    stub_list_services,
)
from mcp_servers.runbooks.server import search_runbooks as _search_runbooks_fn


def _extract_target_service(question: str) -> str:
    """Extracts target microservice name from question if present, defaults to 'payment-service'."""
    lower = question.lower()
    for svc in ("payment-service", "order-service", "inventory-service"):
        if svc in lower or svc.replace("-service", "") in lower:
            return svc
    return "payment-service"


# ---------------------------------------------------------------------------
# Specialist 1: LogAgent
# ---------------------------------------------------------------------------

_LOG_AGENT_PROMPT = """\
You are a specialist Log Analysis SRE Agent for microservices.
Your ONLY responsibility is to investigate structured application logs and identify error patterns.

Investigation:
1. Call get_logs for the target service (request ERROR and CRITICAL lines first).
2. Look for stack traces, exception classes, HTTP 5xx codes, connection refused, or OOM messages.
3. Summarize findings concisely:
   - Primary Error / Exception: Exact error text found.
   - Frequency / Pattern: How often and when it occurs.
   - Suspected Root Cause from Logs: What the logs indicate is wrong.
"""


def _build_log_agent(model_id: str | None = None) -> Any:
    @tool
    def get_logs(service: str, minutes: int = 10, level: str | None = "ERROR") -> str:
        """Fetch application logs filtered by level (ERROR, CRITICAL, WARNING, INFO)."""
        return json.dumps(stub_get_logs(service, minutes, level), indent=2)

    llm = get_llm(model_id=model_id)
    return create_react_agent(
        model=llm,
        tools=[get_logs],
        prompt=_LOG_AGENT_PROMPT,
    )


# ---------------------------------------------------------------------------
# Specialist 2: MetricsAgent
# ---------------------------------------------------------------------------

_METRICS_AGENT_PROMPT = """\
You are a specialist Metrics Analysis SRE Agent for microservices.
Your ONLY responsibility is to investigate Prometheus performance telemetry and container runtime state.

Investigation:
1. Call get_pod_status for the target service to check container state, restart count, and memory limit.
2. Call get_metrics for key metrics: cpu_usage, memory_usage_mb, error_rate, latency_p95_ms.
3. Summarize findings concisely:
   - Pod State & Restarts: Running, exited, oom_killed, or restarting with restart count.
   - Metric Anomalies: Memory near limit, CPU saturated, high error rate, or elevated latency.
   - Suspected Root Cause from Metrics: What the metrics indicate.
"""


def _build_metrics_agent(model_id: str | None = None) -> Any:
    @tool
    def get_pod_status(service: str) -> str:
        """Get container pod status: state, exit_code, oom_killed, restart_count, memory_limit_mb."""
        return json.dumps(stub_get_pod_status(service), indent=2)

    @tool
    def get_metrics(service: str, metric: str, minutes: int = 5) -> str:
        """Get time-series metric samples for a service (cpu_usage, memory_usage_mb, error_rate, latency_p95_ms)."""
        return json.dumps(stub_get_metrics(service, metric, minutes), indent=2)

    llm = get_llm(model_id=model_id)
    return create_react_agent(
        model=llm,
        tools=[get_pod_status, get_metrics],
        prompt=_METRICS_AGENT_PROMPT,
    )


# ---------------------------------------------------------------------------
# Specialist 3: EventsAgent
# ---------------------------------------------------------------------------

_EVENTS_AGENT_PROMPT = """\
You are a specialist Events & Lifecycle SRE Agent for microservices.
Your ONLY responsibility is to inspect Kubernetes and Docker lifecycle events.

Investigation:
1. Call list_services to inspect registered microservices across the stack.
2. Call get_events for the service to check warnings, kills, backoffs, and restarts.
3. Summarize findings concisely:
   - Lifecycle Warning Events: OOM kills, back-offs, unhealthy probes, or container exits.
   - Blast Radius: Whether other services are affected.
"""


def _build_events_agent(model_id: str | None = None) -> Any:
    @tool
    def list_services() -> str:
        """List all microservices and their overall status."""
        return json.dumps(stub_list_services(), indent=2)

    @tool
    def get_events(service: str, minutes: int = 15) -> str:
        """Get recent lifecycle events (warnings, restarts) for a service."""
        return json.dumps(stub_get_events(service, minutes), indent=2)

    llm = get_llm(model_id=model_id)
    return create_react_agent(
        model=llm,
        tools=[list_services, get_events],
        prompt=_EVENTS_AGENT_PROMPT,
    )


# ---------------------------------------------------------------------------
# Coordinator Agent
# ---------------------------------------------------------------------------

_COORDINATOR_PROMPT = """\
You are the Lead SRE Coordinator Agent. You receive diagnostic reports from \
three specialist agents running concurrently (LogAgent, MetricsAgent, EventsAgent).

Your job:
1. Review the specialists' telemetry findings.
2. Call search_runbooks with the specific symptoms identified by the specialists to confirm the playbook and remediation.
3. Synthesize all findings into the standard ChatOps diagnosis format:

OUTPUT FORMAT:
- **Diagnosis**: Root cause with confidence (high / medium / low).
- **Failure Type**: Exactly one standard failure type: out_of_memory | bad_config | health_check_failure | db_timeout | dependency_failure | disk_full | cpu_saturation | crash_loop | network_timeout | high_error_rate | other | unknown
- **Evidence**: Bulleted evidence citing specific log errors, metric numbers, and event warnings.
- **How to confirm**: Diagnostic commands from runbook.
- **Recommended fix**: Step-by-step fix from runbook.
- **Sources**: Runbook titles cited.
"""


def _build_coordinator_agent(model_id: str | None = None) -> Any:
    @tool
    def search_runbooks(query: str, top_k: int = 3) -> str:
        """Search SRE runbooks knowledge base."""
        res = _search_runbooks_fn(query=query, top_k=top_k, include_external=True)
        return json.dumps(res, indent=2)

    llm = get_llm(model_id=model_id)
    return create_react_agent(
        model=llm,
        tools=[search_runbooks],
        prompt=_COORDINATOR_PROMPT,
    )


# ---------------------------------------------------------------------------
# Parallel Orchestrator
# ---------------------------------------------------------------------------


def _run_sub_agent_sync(agent: Any, prompt: str) -> tuple[str, list[dict]]:
    """Helper to run a sub-agent synchronously inside an async worker thread."""
    try:
        res = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        msgs = res.get("messages", [])
        final_msg = msgs[-1] if msgs else None
        text = clean_output(final_msg) if final_msg else ""
        trace = _build_tool_trace(msgs)
        return text, trace
    except Exception as exc:
        return f"Specialist analysis encountered an error: {exc}", []


async def multi_agent_ask_async(
    question: str,
    service: str | None = None,
    model_id: str | None = None,
    stub: bool = True,
) -> dict[str, Any]:
    """
    Executes parallel multi-agent diagnosis via asyncio.gather().

    1. Launches LogAgent, MetricsAgent, and EventsAgent concurrently.
    2. Awaits all 3 specialist analyses.
    3. Feeds pre-analyzed reports into CoordinatorAgent for synthesis and RAG verification.
    """
    target_service = service or _extract_target_service(question)
    t0 = time.perf_counter()

    log_agent = _build_log_agent(model_id=model_id)
    metrics_agent = _build_metrics_agent(model_id=model_id)
    events_agent = _build_events_agent(model_id=model_id)

    log_prompt = f"Target Service: {target_service}\nIncident: {question}\nAnalyze logs for errors and stack traces."
    metrics_prompt = f"Target Service: {target_service}\nIncident: {question}\nAnalyze pod status and Prometheus metrics."
    events_prompt = f"Target Service: {target_service}\nIncident: {question}\nInspect lifecycle events and cluster status."

    # Concurrent execution of the 3 specialists
    (log_text, log_trace), (metrics_text, metrics_trace), (events_text, events_trace) = await asyncio.gather(
        asyncio.to_thread(_run_sub_agent_sync, log_agent, log_prompt),
        asyncio.to_thread(_run_sub_agent_sync, metrics_agent, metrics_prompt),
        asyncio.to_thread(_run_sub_agent_sync, events_agent, events_prompt),
    )

    t_specialists = round(time.perf_counter() - t0, 3)

    # Coordinator synthesis
    coordinator = _build_coordinator_agent(model_id=model_id)
    coord_prompt = (
        f"Incident Question: {question}\n"
        f"Target Service: {target_service}\n\n"
        f"=== LOG AGENT REPORT ===\n{log_text}\n\n"
        f"=== METRICS AGENT REPORT ===\n{metrics_text}\n\n"
        f"=== EVENTS AGENT REPORT ===\n{events_text}\n\n"
        "Synthesize these findings, consult search_runbooks for the official fix, and provide the final diagnosis."
    )

    time.perf_counter()
    coord_res = await asyncio.to_thread(coordinator.invoke, {"messages": [{"role": "user", "content": coord_prompt}]})
    t_total = round(time.perf_counter() - t0, 3)

    coord_msgs = coord_res.get("messages", [])
    final_msg = coord_msgs[-1] if coord_msgs else None
    diagnosis = clean_output(final_msg) if final_msg else ""
    coord_trace = _build_tool_trace(coord_msgs)

    combined_trace = log_trace + metrics_trace + events_trace + coord_trace

    return {
        "question": question,
        "service": target_service,
        "diagnosis": diagnosis,
        "failure_type": _extract_failure_type(diagnosis),
        "confidence": _extract_confidence(diagnosis),
        "tool_trace": combined_trace,
        "sources": _extract_sources(diagnosis),
        "latency_s": t_total,
        "specialists_latency_s": t_specialists,
        "model_id": model_id,
        "pipeline": "Parallel(LogAgent + MetricsAgent + EventsAgent) -> CoordinatorAgent",
        "specialist_reports": {
            "log_agent": log_text,
            "metrics_agent": metrics_text,
            "events_agent": events_text,
        },
    }


def multi_agent_ask(
    question: str,
    service: str | None = None,
    model_id: str | None = None,
    stub: bool = True,
) -> dict[str, Any]:
    """Synchronous entry point for parallel multi-agent diagnosis."""
    return asyncio.run(
        multi_agent_ask_async(
            question=question,
            service=service,
            model_id=model_id,
            stub=stub,
        )
    )
