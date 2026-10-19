"""
LangGraph Tool-Calling ChatOps Agent (Week 2).

Wraps four tools:
  - search_runbooks        : RAG over SRE runbooks (Person A's MCP server)
  - get_metrics            : Live Prometheus metrics  (Person B / stub)
  - get_pod_status         : Container / pod state    (Person B / stub)
  - get_events             : Recent events / logs     (Person B / stub)

Usage:
    # Stub mode (no live infra needed)
    from agent.agent import build_agent
    graph = build_agent(stub=True)
    result = graph.invoke({"messages": [{"role": "user", "content": "Why did payment-service fail?"}]})

    # Real mode (requires MCP servers running)
    graph = build_agent(stub=False, mcp_url="http://localhost:8010")
    ...
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent.llm import get_llm
from agent.stub_tools import (
    stub_get_events,
    stub_get_metrics,
    stub_get_pod_status,
)
from mcp_servers.runbooks.server import search_runbooks as _search_runbooks_fn

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """\
You are an expert AI SRE ChatOps agent. Your job is to diagnose microservice \
incidents by investigating first, citing evidence, and never claiming a root \
cause without a supporting tool result.

INVESTIGATION PROTOCOL (follow in order):
1. ALWAYS call search_runbooks first to find the relevant runbook and known symptoms.
2. Call get_pod_status to confirm whether the container is running, restarting, or OOM-killed.
3. Call get_metrics for CPU, memory, error_rate, and latency to quantify the problem.
4. Call get_events to surface recent lifecycle events (restarts, pulls, warnings).
5. Cross-reference tool results with the runbook before drawing a conclusion.

OUTPUT FORMAT (always follow this structure):
- **Diagnosis**: Root cause with confidence (high / medium / low).
- **Evidence**: Exact values from tool results that support the diagnosis.
- **How to confirm**: Commands from the runbook to verify the issue locally.
- **Recommended fix**: Step-by-step remediation from the runbook.
- **Sources**: Runbook titles and file paths cited.

STRICT RULES:
- Never invent metrics, commands, or causes not returned by a tool or runbook.
- If tools return insufficient data, say so explicitly.
- Always list sources at the end.
"""

# ---------------------------------------------------------------------------
# LangChain tool wrappers
# ---------------------------------------------------------------------------


@tool
def search_runbooks(query: str, top_k: int = 3) -> str:
    """
    Search the ChatOps runbook knowledge base for relevant SRE playbooks.
    Use a natural-language description of the incident symptom as the query.
    Always call this tool first when investigating any service failure.

    Args:
        query: Natural-language description of the incident or symptom.
        top_k: Number of runbook results to return (default 3).

    Returns:
        JSON string with query and list of matching runbook snippets.
    """
    result = _search_runbooks_fn(query=query, top_k=top_k)
    return json.dumps(result, indent=2)


def _make_stub_tools() -> list:
    """Build LangChain tool wrappers around the stub implementations."""

    @tool
    def get_metrics(service: str, metric: str, minutes: int = 5) -> str:
        """
        Retrieve time-series metrics for a service from Prometheus.
        Available metrics: cpu_usage, memory_usage_mb, request_rate,
        error_rate, latency_p95_ms, latency_p99_ms.

        Args:
            service: Service name (e.g. 'payment-service').
            metric:  Metric name.
            minutes: Lookback window in minutes (default 5).

        Returns:
            JSON with latest, min, max values and sample time-series.
        """
        return json.dumps(stub_get_metrics(service, metric, minutes), indent=2)

    @tool
    def get_pod_status(service: str) -> str:
        """
        Get the current container / pod status for a service.
        Returns state (running|restarting|exited|oom_killed|unhealthy|not_found),
        restart count, exit code, OOM flag, health status, and memory limit.

        Args:
            service: Service name (e.g. 'inventory-service').

        Returns:
            JSON with container state and health details.
        """
        return json.dumps(stub_get_pod_status(service), indent=2)

    @tool
    def get_events(service: str, minutes: int = 15) -> str:
        """
        Get recent events (lifecycle, warnings, errors) for a service.
        Useful for understanding what happened leading up to a failure.

        Args:
            service: Service name (e.g. 'order-service').
            minutes: How many minutes back to look (default 15).

        Returns:
            JSON with a list of timestamped events.
        """
        return json.dumps(stub_get_events(service, minutes), indent=2)

    return [get_metrics, get_pod_status, get_events]


# ---------------------------------------------------------------------------
# Agent builder
# ---------------------------------------------------------------------------


def build_agent(stub: bool = True) -> Any:
    """
    Build and return a compiled LangGraph ReAct agent.

    Args:
        stub: If True, use stub implementations for Person B's tools
              (no live infrastructure required). If False, real MCP
              client connections are used (not yet wired — Day 13-14).

    Returns:
        A compiled LangGraph graph that accepts {"messages": [...]} and
        returns {"messages": [...]} with the agent's final answer.
    """
    llm = get_llm()

    # Always include the runbooks tool (our own MCP server, called in-process)
    tools: list = [search_runbooks]

    if stub:
        tools.extend(_make_stub_tools())
    else:
        # Real MCP integration placeholder — to be wired up Days 13-14
        # when Person B's infra MCP servers are running.
        raise NotImplementedError(
            "Real MCP client mode is not yet wired. "
            "Run with stub=True until Person B's infra servers are available."
        )

    graph = create_react_agent(
        model=llm,
        tools=tools,
        prompt=AGENT_SYSTEM_PROMPT,
    )
    return graph


def ask(question: str, stub: bool = True) -> dict[str, Any]:
    """
    Public entry point for external callers (CLI, Slack, tests).

    Args:
        question: Natural-language incident question.
        stub:     Whether to use stub tools.

    Returns:
        {
            "question": str,
            "answer":   str,   # agent's final message content
            "messages": list,  # full message history
        }
    """
    graph = build_agent(stub=stub)
    result = graph.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    messages = result.get("messages", [])
    # Last message is the AI's final answer
    final = messages[-1].content if messages else ""
    return {
        "question": question,
        "answer": final,
        "messages": [
            {"role": getattr(m, "type", "unknown"), "content": m.content}
            for m in messages
        ],
    }
