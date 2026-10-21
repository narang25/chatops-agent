"""
Prometheus Metrics MCP Server (mcp v2 / MCPServer API).

Exposes the tool:
    get_metrics(service, metric, minutes=5)
Shape matches contracts/mcp_tools.md exactly.

Run via stdio transport:
    python -m mcp_servers.prometheus.server
"""

import os
import sys
import time
from pathlib import Path
from typing import Any
import httpx

# Ensure project root is importable regardless of cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.mcpserver import MCPServer

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
DEFAULT_TIMEOUT_S = 4.0

VALID_SERVICES = {
    "payment-service",
    "order-service",
    "inventory-service",
}

# Whitelist mapping: metric name -> PromQL query template parameterized by {service}
METRIC_QUERY_TEMPLATES: dict[str, str] = {
    # Contract metrics
    "http_requests_total": 'sum(http_requests_total{{service="{service}"}})',
    "http_request_duration_seconds": 'sum(rate(http_request_duration_seconds_sum{{service="{service}"}}[1m])) / sum(rate(http_request_duration_seconds_count{{service="{service}"}}[1m]))',
    "app_errors_total": 'sum(app_errors_total{{service="{service}"}})',
    "app_memory_bytes": 'sum(app_memory_bytes{{service="{service}"}})',
    "app_up": 'sum(app_up{{service="{service}"}})',
    # cAdvisor container metrics
    "container_memory_usage_bytes": 'sum(container_memory_usage_bytes{{name="{service}"}})',
    "container_spec_memory_limit_bytes": 'sum(container_spec_memory_limit_bytes{{name="{service}"}})',
    "container_cpu_usage_seconds_total": 'sum(rate(container_cpu_usage_seconds_total{{name="{service}"}}[1m]))',
    # Semantic aliases used by agent
    "request_rate": 'sum(rate(http_requests_total{{service="{service}"}}[1m]))',
    "error_rate": 'sum(rate(app_errors_total{{service="{service}"}}[1m]))',
    "cpu_usage": 'sum(rate(container_cpu_usage_seconds_total{{name="{service}"}}[1m]))',
    "memory_usage_mb": 'sum(app_memory_bytes{{service="{service}"}}) / 1048576',
    "latency_p95_ms": 'sum(rate(http_request_duration_seconds_sum{{service="{service}"}}[1m])) / sum(rate(http_request_duration_seconds_count{{service="{service}"}}[1m])) * 1000',
    "latency_p99_ms": 'sum(rate(http_request_duration_seconds_sum{{service="{service}"}}[1m])) / sum(rate(http_request_duration_seconds_count{{service="{service}"}}[1m])) * 1000',
}

mcp = MCPServer(
    name="chatops-prometheus",
    version="1.0.0",
    description="Prometheus time-series metrics MCP server for ChatOps microservices.",
)


def _query_prometheus(promql: str, start_ts: float, end_ts: float, step: int = 15) -> list[list]:
    """Execute query_range against Prometheus HTTP API."""
    url = f"{PROMETHEUS_URL}/api/v1/query_range"
    params = {
        "query": promql,
        "start": str(start_ts),
        "end": str(end_ts),
        "step": f"{step}s",
    }
    with httpx.Client(timeout=DEFAULT_TIMEOUT_S) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "success":
        raise ValueError(f"Prometheus query returned status {data.get('status')}")

    results = data.get("data", {}).get("result", [])
    if not results:
        return []

    # Take first series or sum of series
    values = results[0].get("values", [])
    samples = []
    for ts, val_str in values:
        try:
            val = float(val_str)
            samples.append([int(ts), round(val, 4)])
        except (ValueError, TypeError):
            continue
    return samples


@mcp.tool(
    description=(
        "Retrieve time-series metric samples for a microservice. "
        "Allowed metrics: http_requests_total, http_request_duration_seconds, "
        "app_errors_total, app_memory_bytes, app_up, container_memory_usage_bytes, "
        "container_spec_memory_limit_bytes, container_cpu_usage_seconds_total, "
        "request_rate, error_rate, cpu_usage, memory_usage_mb, latency_p95_ms. "
        "Returns latest, min, max, and timestamped samples."
    )
)
def get_metrics(service: str, metric: str, minutes: int = 5) -> dict[str, Any]:
    """
    Retrieve time-series metric samples for a service.

    Args:
        service: Microservice name ('payment-service' | 'order-service' | 'inventory-service')
        metric: Metric identifier from allowed whitelist
        minutes: Lookback time window in minutes (default 5, max 60)

    Returns:
        Contract shape matching contracts/mcp_tools.md
    """
    if service not in VALID_SERVICES:
        return {
            "error": f"Invalid service '{service}'. Must be one of: {sorted(VALID_SERVICES)}"
        }

    if metric not in METRIC_QUERY_TEMPLATES:
        return {
            "error": f"Invalid metric '{metric}'. Must be one of: {sorted(METRIC_QUERY_TEMPLATES.keys())}"
        }

    minutes = max(1, min(int(minutes), 60))
    now = time.time()
    start_ts = now - (minutes * 60)
    step = max(5, int((minutes * 60) / 20))

    promql = METRIC_QUERY_TEMPLATES[metric].format(service=service)

    try:
        samples = _query_prometheus(promql, start_ts, now, step=step)
        if samples:
            values = [s[1] for s in samples]
            latest = values[-1]
            min_val = min(values)
            max_val = max(values)
        else:
            latest = None
            min_val = None
            max_val = None

        return {
            "service": service,
            "metric": metric,
            "window_minutes": minutes,
            "latest": latest,
            "min": min_val,
            "max": max_val,
            "samples": samples,
        }
    except Exception as exc:
        return {"error": f"Prometheus query failed for {service}/{metric}: {exc}"}


if __name__ == "__main__":
    mcp.run_stdio_async()
