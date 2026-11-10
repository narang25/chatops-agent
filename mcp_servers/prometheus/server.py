"""
Prometheus Metrics & Anomaly MCP Server (mcp v2 / MCPServer API).

Exposes the tools:
    get_metrics(service, metric, minutes=5)
    get_anomalies(service, minutes=10)

Shapes match contracts/mcp_tools.md.

Run via stdio transport:
    python -m mcp_servers.prometheus.server
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Ensure project root is importable regardless of cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.mcpserver import MCPServer

try:
    from drain3 import TemplateMiner
    from drain3.template_miner_config import TemplateMinerConfig

    _DRAIN3_AVAILABLE = True
except ImportError:
    _DRAIN3_AVAILABLE = False

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

# Core metrics evaluated for anomaly detection between baseline and current window
ANOMALY_EVAL_METRICS = [
    "error_rate",
    "latency_p95_ms",
    "memory_usage_mb",
    "cpu_usage",
]

mcp = MCPServer(
    name="chatops-prometheus",
    version="1.1.0",
    description="Prometheus time-series metrics & anomaly detection MCP server for ChatOps microservices.",
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

    values = results[0].get("values", [])
    samples = []
    for ts, val_str in values:
        try:
            val = float(val_str)
            samples.append([int(ts), round(val, 4)])
        except (ValueError, TypeError):
            continue
    return samples


def _fetch_container_logs(service: str, since_ts: float, until_ts: float) -> list[dict]:
    """Fetch parsed JSON logs from container for given epoch timestamp range."""
    since_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(since_ts))
    cmd = ["docker", "logs", "--since", since_str, service]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3.0)
        lines = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                lines.append(obj)
            except Exception:
                lines.append({"message": line, "level": "INFO", "timestamp": since_str})
        return lines
    except Exception:
        return []


def _extract_log_patterns(log_lines: list[dict]) -> dict[str, dict]:
    """Use Drain3 template miner to group logs into structured patterns."""
    if not _DRAIN3_AVAILABLE:
        # Simple fallback clusterer
        patterns: dict[str, dict] = {}
        for entry in log_lines:
            msg = entry.get("message", "")
            prefix = " ".join(msg.split()[:5]) if msg else "empty"
            if prefix not in patterns:
                patterns[prefix] = {
                    "pattern": prefix + " ...",
                    "count": 0,
                    "sample": msg,
                    "first_seen": entry.get("timestamp", ""),
                }
            patterns[prefix]["count"] += 1
        return patterns

    config = TemplateMinerConfig()
    config.drain_sim_th = 0.5
    miner = TemplateMiner(config=config)
    pattern_meta: dict[str, dict] = {}

    for entry in log_lines:
        msg = entry.get("message", "")
        if not msg:
            continue
        res = miner.add_log_message(msg)
        template = res.get("template_mined", msg)
        if template not in pattern_meta:
            pattern_meta[template] = {
                "pattern": template,
                "count": 0,
                "sample": msg,
                "first_seen": entry.get("timestamp", ""),
            }
        pattern_meta[template]["count"] += 1

    return pattern_meta


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
    """Retrieve time-series metric samples for a service."""
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


@mcp.tool(
    description=(
        "Detect metric and log anomalies by comparing the recent time window against "
        "a prior baseline window of the same duration. Evaluates error_rate, latency_p95_ms, "
        "memory_usage_mb, and cpu_usage. Clusters recent logs with Drain3 to highlight newly emerging error patterns."
    )
)
def get_anomalies(service: str, minutes: int = 10) -> dict[str, Any]:
    """
    Detect metric anomalies and newly observed log patterns.

    Args:
        service: Microservice name ('payment-service' | 'order-service' | 'inventory-service')
        minutes: Window duration in minutes (compares [now-minutes, now] against [now-2*minutes, now-minutes])

    Returns:
        Contract shape: {service, window_minutes, metric_anomalies, log_anomalies}
    """
    if service not in VALID_SERVICES:
        return {
            "error": f"Invalid service '{service}'. Must be one of: {sorted(VALID_SERVICES)}"
        }

    minutes = max(2, min(int(minutes), 60))
    now = time.time()
    current_start = now - (minutes * 60)
    baseline_start = now - (2 * minutes * 60)

    metric_anomalies: list[dict[str, Any]] = []

    # 1. Compare metric baseline vs current window
    for metric_name in ANOMALY_EVAL_METRICS:
        promql = METRIC_QUERY_TEMPLATES[metric_name].format(service=service)
        try:
            baseline_samples = _query_prometheus(promql, baseline_start, current_start, step=max(5, int(minutes * 60 / 10)))
            current_samples = _query_prometheus(promql, current_start, now, step=max(5, int(minutes * 60 / 10)))

            if not current_samples:
                continue

            baseline_vals = [s[1] for s in baseline_samples] if baseline_samples else []
            current_vals = [s[1] for s in current_samples]

            baseline_avg = sum(baseline_vals) / len(baseline_vals) if baseline_vals else 0.0
            current_avg = sum(current_vals) / len(current_vals) if current_vals else 0.0

            # Compute change percentage
            if baseline_avg > 0:
                change_pct = round(((current_avg - baseline_avg) / baseline_avg) * 100, 2)
            elif current_avg > 0:
                change_pct = 100.0
            else:
                change_pct = 0.0

            # Filter out insignificant changes (< 20%)
            if abs(change_pct) >= 20.0:
                direction = "up" if change_pct > 0 else "down"
                metric_anomalies.append({
                    "metric": metric_name,
                    "change_pct": change_pct,
                    "baseline": round(baseline_avg, 4),
                    "current": round(current_avg, 4),
                    "direction": direction,
                })
        except Exception:
            continue

    # Sort largest change first
    metric_anomalies.sort(key=lambda m: abs(m["change_pct"]), reverse=True)

    # 2. Extract and compare log patterns using Drain3
    baseline_logs = _fetch_container_logs(service, baseline_start, current_start)
    current_logs = _fetch_container_logs(service, current_start, now)

    baseline_patterns = set(_extract_log_patterns(baseline_logs).keys())
    current_patterns_map = _extract_log_patterns(current_logs)

    new_log_anomalies: list[dict[str, Any]] = []
    for pattern_str, meta in current_patterns_map.items():
        if pattern_str not in baseline_patterns:
            new_log_anomalies.append({
                "pattern": meta["pattern"],
                "count": meta["count"],
                "first_seen": meta["first_seen"],
                "sample": meta["sample"],
            })

    new_log_anomalies.sort(key=lambda x: x["count"], reverse=True)

    return {
        "service": service,
        "window_minutes": minutes,
        "metric_anomalies": metric_anomalies,
        "log_anomalies": new_log_anomalies[:10],
    }


if __name__ == "__main__":
    mcp.run_stdio_async()
