"""
Stub implementations of Person B's three MCP tools.

Used when running the agent in --stub mode (no live infrastructure needed).
Each stub returns plausible, realistic data that exercises the agent's
reasoning path without requiring Docker, Prometheus, or Kubernetes.

Stubs are keyed on the `service` argument and accept the same signatures
as the real MCP tools defined in contracts/mcp_tools.md.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Realistic baseline data per service
# ---------------------------------------------------------------------------

_SERVICE_PROFILES: dict[str, dict] = {
    "payment-service": {
        "port": 8001,
        "cpu_normal": 0.25,
        "memory_normal_mb": 48,
        "restart_count": 0,
        "state": "running",
        "health": "healthy",
    },
    "inventory-service": {
        "port": 8002,
        "cpu_normal": 0.15,
        "memory_normal_mb": 32,
        "restart_count": 0,
        "state": "running",
        "health": "healthy",
    },
    "order-service": {
        "port": 8003,
        "cpu_normal": 0.18,
        "memory_normal_mb": 36,
        "restart_count": 0,
        "state": "running",
        "health": "healthy",
    },
}

_FALLBACK_PROFILE = {
    "port": 8080,
    "cpu_normal": 0.20,
    "memory_normal_mb": 40,
    "restart_count": 0,
    "state": "running",
    "health": "healthy",
}


def _profile(service: str) -> dict:
    return _SERVICE_PROFILES.get(service, _FALLBACK_PROFILE)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _make_samples(baseline: float, minutes: int, jitter: float = 0.05) -> list:
    """Generate (unix_ts, value) samples at 30-second intervals."""
    import time as _time

    now = _time.time()
    samples = []
    for i in range(minutes * 2):
        ts = now - (minutes * 60) + i * 30
        delta = random.uniform(-jitter, jitter) if jitter > 0 else 0.0
        value = max(0.0, round(baseline + delta, 4))
        samples.append([round(ts), value])
    return samples


# ---------------------------------------------------------------------------
# Stub tool functions — same signatures as contracts/mcp_tools.md
# ---------------------------------------------------------------------------


def stub_get_metrics(service: str, metric: str, minutes: int = 5) -> dict:
    """
    Returns synthetic metric samples for a service.

    Healthy baseline services return 0.0 error_rate and low latency so
    unrelated queries do not pick up spurious stub failures. Unknown metrics
    return null values to simulate an uninstrumented metric.
    """
    p = _profile(service)
    is_healthy = p["state"] == "running" and p["health"] == "healthy"

    metric_specs: dict[str, tuple[float, float]] = {
        "cpu_usage": (p["cpu_normal"], 0.02),
        "memory_usage_mb": (p["memory_normal_mb"], 0.5),
        "request_rate": (round(random.uniform(8.0, 20.0), 2), 0.5),
        "error_rate": (0.0 if is_healthy else 0.25, 0.0 if is_healthy else 0.02),
        "latency_p95_ms": (14.0 if is_healthy else 450.0, 2.0),
        "latency_p99_ms": (28.0 if is_healthy else 900.0, 3.0),
    }

    if metric not in metric_specs:
        return {
            "service": service,
            "metric": metric,
            "window_minutes": minutes,
            "latest": None,
            "min": None,
            "max": None,
            "samples": [],
        }

    baseline, jitter = metric_specs[metric]
    samples = _make_samples(baseline, minutes, jitter=jitter)
    values = [v for _, v in samples]
    return {
        "service": service,
        "metric": metric,
        "window_minutes": minutes,
        "latest": round(values[-1], 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "samples": samples,
    }


def stub_get_pod_status(service: str) -> dict:
    """Returns a synthetic container status for a service."""
    try:
        from mcp_servers.runbooks.evidence_gate import record_evidence
        record_evidence("stub_get_pod_status", service=service)
    except Exception:
        pass
    p = _profile(service)
    if p["state"] not in {"running", "restarting", "exited", "oom_killed", "unhealthy", "not_found"}:
        state = "running"
    else:
        state = p["state"]

    return {
        "service": service,
        "state": state,
        "restart_count": p["restart_count"],
        "exit_code": None if state == "running" else 1,
        "oom_killed": state == "oom_killed",
        "health": p["health"],
        "started_at": _now_iso(),
        "memory_limit_mb": p["memory_normal_mb"] * 2,
    }


def stub_get_events(service: str, minutes: int = 15) -> dict:
    """Returns synthetic event log for a service."""
    return {
        "service": service,
        "events": [
            {
                "timestamp": _now_iso(),
                "type": "Normal",
                "reason": "Started",
                "message": f"{service} container started successfully.",
            },
            {
                "timestamp": _now_iso(),
                "type": "Normal",
                "reason": "Pulled",
                "message": f"Successfully pulled image for {service}.",
            },
        ],
    }


def stub_list_services() -> dict:
    """Returns a synthetic list of registered microservices and their states."""
    try:
        from mcp_servers.runbooks.evidence_gate import record_evidence
        record_evidence("stub_list_services")
    except Exception:
        pass
    services = []
    for svc_name in ["payment-service", "order-service", "inventory-service"]:
        p = _profile(svc_name)
        services.append({"name": svc_name, "state": p.get("state", "running")})
    return {"services": services}


def stub_get_logs(
    service: str,
    minutes: int = 10,
    level: str | None = None,
    limit: int = 100,
) -> dict:
    """Returns synthetic application log lines for a service."""
    try:
        from mcp_servers.runbooks.evidence_gate import record_evidence
        record_evidence("stub_get_logs", service=service)
    except Exception:
        pass
    p = _profile(service)
    state = p.get("state", "running")
    now = _now_iso()

    sample_lines = [
        {"timestamp": now, "level": "INFO", "message": f"{service} listening on port {p.get('port', 8080)}."},
        {"timestamp": now, "level": "INFO", "message": "Healthcheck probe 200 OK."},
    ]

    if state == "oom_killed":
        sample_lines.append(
            {"timestamp": now, "level": "CRITICAL", "message": "Memory allocation failed: Out of memory (kill signal received)."}
        )
    elif state in ("exited", "restarting"):
        sample_lines.append(
            {"timestamp": now, "level": "ERROR", "message": f"{service} encountered fatal error or missing config."}
        )
    elif state == "unhealthy":
        sample_lines.append(
            {"timestamp": now, "level": "WARNING", "message": "Health check probe failed: response timeout."}
        )

    if level:
        lvl = level.upper()
        sample_lines = [line for line in sample_lines if line["level"] == lvl]

    sample_lines = sample_lines[:limit]
    return {
        "service": service,
        "count": len(sample_lines),
        "lines": sample_lines,
    }


def stub_propose_remediation(
    service: str,
    action: str,
    params: dict | None = None,
) -> dict:
    """
    Simulates proposal of a remediation plan (Task A21 / contracts/mcp_tools.md).
    Generates a dry-run proposal with risk assessment.
    STRICT SAFETY RULE: This tool NEVER executes any modification.
    """
    import time as _time

    params = params or {}
    proposal_id = f"prop_{service}_{int(_time.time())}"

    # Policy Denials
    if service in ("postgres", "database", "prometheus"):
        return {
            "error": f"Policy Violation: Automated remediation is forbidden on core infrastructure '{service}'."
        }

    action_lower = action.lower()
    if action_lower == "set_memory_limit":
        limit_mb = params.get("limit_mb", 256)
        changes = [
            f"Update container memory limit for {service} to {limit_mb}MB",
            f"Graceful restart of {service} to apply cgroup memory limit",
        ]
        risk = "low"
    elif action_lower in ("restart_service", "restart"):
        changes = [f"Issue SIGTERM to {service} container followed by fresh container start"]
        risk = "medium"
    elif action_lower in ("rollback_deploy", "rollback"):
        changes = [f"Revert {service} image deployment to previous known healthy release"]
        risk = "medium"
    elif action_lower in ("scale_replicas", "scale"):
        replicas = params.get("replicas", 2)
        changes = [f"Scale {service} deployment to {replicas} replicas"]
        risk = "low"
    else:
        changes = [f"Perform {action} with parameters {params}"]
        risk = "high"

    return {
        "proposal_id": proposal_id,
        "action": action,
        "params": params,
        "dry_run": {
            "changes": changes,
            "risk": risk,
        },
        "requires_approval": True,
    }
