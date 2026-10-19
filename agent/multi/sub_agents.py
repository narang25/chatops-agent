"""
Multi-Agent Architecture Skeleton  (Week 3 -- Task A13)
========================================================

Architecture Overview
---------------------
The multi-agent system decomposes the monolithic SRE agent into three
specialised sub-agents, each expert in one signal domain:

  LogAgent      -- parses stack traces, error messages, and log patterns
  MetricsAgent  -- analyses Prometheus CPU/memory/latency/error-rate trends
  CoordinatorAgent -- synthesises hypotheses from sub-agents + computes confidence

Coordinator flow:
  User Query
      |
      v
  CoordinatorAgent
    |         |         |
    v         v         v
  LogAgent  MetricsAgent  (RunbookRAG: already handled via search_runbooks)
    |         |
    v         v
  CoordinatorAgent (synthesis + final answer)

Why multi-agent?
  - Parallelism: Log and Metrics agents can run simultaneously.
  - Specialisation: Each sub-agent has a focused, smaller system prompt → less
    hallucination, better tool use.
  - Scalability: New signal domains (traces, cost, SLO budget) can be added as
    independent agents without touching the coordinator.

Status: Week 3 skeleton (orchestration logic stubbed).
        Full parallel execution planned for Week 4.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent.llm import get_llm
from agent.stub_tools import stub_get_events, stub_get_metrics, stub_get_pod_status
from mcp_servers.runbooks.server import search_runbooks as _search_runbooks_fn

# ---------------------------------------------------------------------------
# Sub-Agent 1: Log Agent
# ---------------------------------------------------------------------------

_LOG_AGENT_PROMPT = """\
You are a specialist Log Analysis Agent for a microservice SRE system.
Your ONLY job is to analyse log lines, stack traces, and event sequences.

Focus on:
- Exception class names and messages
- Error codes (HTTP status, exit codes, errno)
- Repeated patterns or anomalous sequences
- Timestamps and ordering of events

RULES:
- Only use get_events to fetch log/event data.
- Never invent log content.
- Output a JSON summary with: log_patterns, error_codes, suspicious_events.
"""


@tool
def get_events_for_logs(service: str, minutes: int = 15) -> str:
    """Fetch recent events and log lines for a service for log analysis."""
    return json.dumps(stub_get_events(service, minutes), indent=2)


def build_log_agent() -> Any:
    """Return a compiled LangGraph log analysis sub-agent."""
    llm = get_llm()
    return create_react_agent(
        model=llm,
        tools=[get_events_for_logs],
        prompt=_LOG_AGENT_PROMPT,
    )


# ---------------------------------------------------------------------------
# Sub-Agent 2: Metrics Agent
# ---------------------------------------------------------------------------

_METRICS_AGENT_PROMPT = """\
You are a specialist Metrics Analysis Agent for a microservice SRE system.
Your ONLY job is to analyse numeric performance signals: CPU, memory, latency, error rate.

Focus on:
- Whether any metric is above dangerous thresholds (CPU > 80%, error_rate > 5%)
- Memory usage relative to the container limit
- Latency spikes (p95 > 500ms is concerning, p99 > 1000ms is critical)
- Trends: is the metric rising, stable, or improving?

RULES:
- Only use get_metrics and get_pod_status to fetch data.
- Never invent metric values.
- Output a JSON summary with: metric_anomalies, pod_state, thresholds_exceeded.
"""


@tool
def get_metrics_for_analysis(service: str, metric: str, minutes: int = 5) -> str:
    """Fetch time-series metrics for a service for metrics analysis."""
    return json.dumps(stub_get_metrics(service, metric, minutes), indent=2)


@tool
def get_pod_status_for_analysis(service: str) -> str:
    """Fetch container/pod status for metrics analysis."""
    return json.dumps(stub_get_pod_status(service), indent=2)


def build_metrics_agent() -> Any:
    """Return a compiled LangGraph metrics analysis sub-agent."""
    llm = get_llm()
    return create_react_agent(
        model=llm,
        tools=[get_metrics_for_analysis, get_pod_status_for_analysis],
        prompt=_METRICS_AGENT_PROMPT,
    )


# ---------------------------------------------------------------------------
# Sub-Agent 3: Coordinator Agent
# ---------------------------------------------------------------------------

_COORDINATOR_PROMPT = """\
You are the Coordinator Agent for a multi-agent ChatOps SRE system.
You receive pre-processed analysis from specialist sub-agents and runbook search results.
Your job is to synthesise all signals into a final, evidence-backed incident diagnosis.

Input you will receive:
  - log_analysis:     Output from the Log Agent (error patterns, exception types)
  - metrics_analysis: Output from the Metrics Agent (anomalous metrics, pod state)
  - runbook_results:  Relevant runbooks from the vector search

Your output MUST follow:
- **Diagnosis**: Root cause with confidence (high / medium / low).
- **Failure Type**: Exactly one failure type from the approved list.
- **Evidence**: Synthesised from log + metrics + runbook signals.
- **Recommended fix**: From runbook, verified against metrics.
- **Sources**: All runbook titles cited.

RULES:
- You may call search_runbooks once to validate or supplement sub-agent findings.
- Never contradict clear tool evidence.
- Confidence = high only if all three signals agree.
"""


@tool
def search_runbooks_coordinator(query: str, top_k: int = 3) -> str:
    """Search runbooks from the Coordinator Agent to validate sub-agent findings."""
    result = _search_runbooks_fn(query=query, top_k=top_k)
    return json.dumps(result, indent=2)


def build_coordinator_agent() -> Any:
    """Return a compiled LangGraph coordinator agent."""
    llm = get_llm()
    return create_react_agent(
        model=llm,
        tools=[search_runbooks_coordinator],
        prompt=_COORDINATOR_PROMPT,
    )


# ---------------------------------------------------------------------------
# Orchestrator (Week 4 target: fully parallel via asyncio)
# ---------------------------------------------------------------------------


def multi_agent_ask(question: str, service: str) -> dict[str, Any]:
    """
    Orchestrate the full multi-agent pipeline (sequential stub for Week 3).

    Week 4 target: run LogAgent and MetricsAgent in parallel via asyncio.gather,
    then pass both results to CoordinatorAgent.

    Args:
        question: Natural-language incident question.
        service:  Service name to investigate.

    Returns:
        Final coordinator diagnosis dict.
    """
    # Step 1: Log Agent analyses events
    log_agent = build_log_agent()
    log_result = log_agent.invoke(
        {"messages": [{"role": "user", "content": f"Analyse logs for {service}. {question}"}]}
    )
    log_summary = log_result["messages"][-1].content if log_result.get("messages") else ""

    # Step 2: Metrics Agent analyses performance signals
    metrics_agent = build_metrics_agent()
    metrics_result = metrics_agent.invoke(
        {"messages": [{"role": "user", "content": f"Analyse metrics for {service}. {question}"}]}
    )
    metrics_summary = metrics_result["messages"][-1].content if metrics_result.get("messages") else ""

    # Step 3: Coordinator synthesises both analyses
    coordinator = build_coordinator_agent()
    synthesis_prompt = (
        f"Incident question: {question}\n\n"
        f"LOG ANALYSIS:\n{log_summary}\n\n"
        f"METRICS ANALYSIS:\n{metrics_summary}\n\n"
        "Please synthesise the above sub-agent findings into a final diagnosis."
    )
    coord_result = coordinator.invoke(
        {"messages": [{"role": "user", "content": synthesis_prompt}]}
    )
    final_answer = coord_result["messages"][-1].content if coord_result.get("messages") else ""

    return {
        "question": question,
        "service": service,
        "log_analysis": log_summary,
        "metrics_analysis": metrics_summary,
        "final_diagnosis": final_answer,
        "pipeline": "LogAgent -> MetricsAgent -> CoordinatorAgent",
    }
