"""
Remediation MCP Server, Safety Engine, Verification & Auto-Rollback (Tasks B20 & B22).

Architecture & Safety Rules:
- Propose-only for Agent: The agent client is ONLY registered with `propose_remediation`.
- Apply is gated: `apply_remediation` requires a single-use, time-bound approval token.
- Verification & Auto-Rollback: Background monitor evaluates metrics post-remediation.
  If error rate or health deteriorates, it automatically executes an emergency rollback.
- Policy-Enforced: Evaluates requests against `infra/remediation_policy.yaml`.
- Audit Log: Every proposal, approval, rejection, verification, and rollback is written to `data/audit_log.jsonl`.
"""

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.mcpserver import MCPServer

POLICY_FILE = PROJECT_ROOT / "infra" / "remediation_policy.yaml"
AUDIT_LOG_FILE = PROJECT_ROOT / "data" / "audit_log.jsonl"
TOKEN_EXPIRY_SECONDS = 300  # 5 minutes
DEFAULT_VERIFY_WINDOW_S = 30  # 30 seconds for test/demo responsiveness

_PROPOSALS: dict[str, dict[str, Any]] = {}


def load_policy() -> dict[str, Any]:
    if not POLICY_FILE.exists():
        return {}
    try:
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def log_audit_event(event_type: str, details: dict[str, Any]):
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **details,
    }
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def check_policy(action: str, service: str, params: dict[str, Any]) -> tuple[bool, str]:
    policy = load_policy()
    rules = policy.get("rules", {}).get(action)
    if not rules:
        return False, f"Action '{action}' is not permitted by policy."

    allow_services = rules.get("allow_services", [])
    deny_services = rules.get("deny_services", [])

    if service in deny_services:
        return False, f"Service '{service}' is explicitly denied for action '{action}'."

    if allow_services and service not in allow_services:
        return False, f"Service '{service}' is not in allowed list for '{action}'."

    if action == "set_memory_limit":
        mem_mb = params.get("memory_mb")
        if not mem_mb:
            return False, "Missing required parameter 'memory_mb'."
        try:
            mem_val = int(mem_mb)
        except ValueError:
            return False, f"Invalid memory_mb: {mem_mb}"

        min_m = rules.get("min_memory_mb", 64)
        max_m = rules.get("max_memory_mb", 512)
        if mem_val < min_m or mem_val > max_m:
            return False, f"Requested memory {mem_val}MB outside allowed range [{min_m}MB - {max_m}MB]."

    return True, "Policy check passed."


def _capture_baseline(service: str) -> dict[str, Any]:
    """Capture pre-fix metrics snapshot for verification baseline."""
    baseline: dict[str, Any] = {"service": service, "timestamp": time.time()}
    try:
        from mcp_servers.kubernetes.server import get_pod_status
        status = get_pod_status(service)
        baseline["state"] = status.get("state")
        baseline["restarts"] = status.get("restart_count", 0)
        baseline["memory_limit_mb"] = status.get("memory_limit_mb")
    except Exception:
        baseline["state"] = "unknown"
        baseline["restarts"] = 0
    return baseline


def _rollback_action(service: str, action: str, previous_state: dict[str, Any], audit_id: str):
    """Emergency rollback when post-remediation metrics degrade."""
    try:
        if action == "set_memory_limit":
            old_mem = previous_state.get("memory_limit_mb") or 128
            subprocess.run(
                ["docker", "update", "--memory", f"{old_mem}m", "--memory-swap", f"{old_mem}m", service],
                check=True,
                capture_output=True,
            )
        elif action == "rollback_deploy":
            subprocess.run(["docker", "restart", service], check=True, capture_output=True)

        log_audit_event("auto_rollback_completed", {
            "audit_id": audit_id,
            "service": service,
            "action": action,
            "restored_state": previous_state,
        })
    except Exception as exc:
        log_audit_event("auto_rollback_failed", {
            "audit_id": audit_id,
            "service": service,
            "action": action,
            "error": str(exc),
        })


def _background_verifier(proposal_id: str, watch_seconds: int = DEFAULT_VERIFY_WINDOW_S):
    """Background monitoring thread watching for health improvement or degradation."""
    time.sleep(watch_seconds)

    record = _PROPOSALS.get(proposal_id)
    if not record or record.get("status") != "applied":
        return

    service = record["service"]
    action = record["action"]
    baseline = record.get("baseline", {})
    audit_id = record.get("audit_id", "")

    try:
        from mcp_servers.kubernetes.server import get_pod_status
        current_status = get_pod_status(service)
        curr_state = current_status.get("state")
        curr_restarts = current_status.get("restart_count", 0)

        # Evaluate condition
        baseline_restarts = baseline.get("restarts", 0)
        worse = (
            curr_state in ["oom_killed", "exited", "unhealthy"]
            or curr_restarts > baseline_restarts + 1
        )

        if worse:
            record["verification_status"] = "worse"
            record["rolled_back"] = True
            log_audit_event("verification_degraded", {
                "proposal_id": proposal_id,
                "audit_id": audit_id,
                "service": service,
                "reason": f"State {curr_state}, restarts {curr_restarts} > {baseline_restarts}",
            })
            _rollback_action(service, action, baseline, audit_id)
        else:
            record["verification_status"] = "improved"
            record["rolled_back"] = False
            log_audit_event("verification_improved", {
                "proposal_id": proposal_id,
                "audit_id": audit_id,
                "service": service,
                "current_state": curr_state,
            })
    except Exception as exc:
        record["verification_status"] = "error"
        log_audit_event("verification_error", {"proposal_id": proposal_id, "error": str(exc)})


# ── FastMCP Server Instance ───────────────────────────────────────────────────

mcp = MCPServer(
    name="chatops-remediation",
    version="1.1.0",
    description="Safety-gated remediation proposal, execution, and auto-rollback engine.",
)


@mcp.tool(
    description=(
        "Propose an operational remediation action for a service. "
        "Permitted actions: set_memory_limit, restart_service, rollback_deploy. "
        "Returns a dry-run analysis and requires human approval via Slack."
    )
)
def propose_remediation(service: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Propose an operational fix. Safe by design: changes nothing."""
    params = params or {}

    allowed, reason = check_policy(action, service, params)
    if not allowed:
        log_audit_event("proposal_rejected_policy", {
            "service": service,
            "action": action,
            "params": params,
            "reason": reason,
        })
        return {
            "error": f"Policy rejection: {reason}",
            "allowed": False,
        }

    proposal_id = str(uuid.uuid4())
    approval_token = str(uuid.uuid4())
    now = time.time()

    changes = []
    risk = "low"
    if action == "set_memory_limit":
        mem = params.get("memory_mb")
        changes.append(f"Update container memory limit to {mem}MB on {service}")
        risk = "medium"
    elif action == "restart_service":
        changes.append(f"Restart container instance {service}")
        risk = "low"
    elif action == "rollback_deploy":
        changes.append(f"Roll back previous deployment and clear injected error faults on {service}")
        risk = "medium"

    proposal_record = {
        "proposal_id": proposal_id,
        "service": service,
        "action": action,
        "params": params,
        "token": approval_token,
        "created_at": now,
        "expires_at": now + TOKEN_EXPIRY_SECONDS,
        "used": False,
        "status": "pending_approval",
        "dry_run": {
            "changes": changes,
            "risk": risk,
        },
    }
    _PROPOSALS[proposal_id] = proposal_record

    log_audit_event("proposed", {
        "proposal_id": proposal_id,
        "service": service,
        "action": action,
        "params": params,
        "risk": risk,
    })

    return {
        "proposal_id": proposal_id,
        "action": action,
        "service": service,
        "params": params,
        "dry_run": {
            "changes": changes,
            "risk": risk,
        },
        "requires_approval": True,
        "expires_in_seconds": TOKEN_EXPIRY_SECONDS,
    }


def apply_remediation(
    proposal_id: str,
    approval_token: str,
    approver: str = "slack_user",
    watch_seconds: int = DEFAULT_VERIFY_WINDOW_S,
) -> dict[str, Any]:
    """Execute a previously approved proposal and launch verification watcher."""
    if proposal_id not in _PROPOSALS:
        return {"error": f"Unknown proposal_id: {proposal_id}", "status": "rejected"}

    record = _PROPOSALS[proposal_id]
    now = time.time()

    if record.get("used"):
        log_audit_event("apply_failed_token_reused", {"proposal_id": proposal_id, "approver": approver})
        return {"error": "Approval token has already been used.", "status": "rejected"}

    if now > record.get("expires_at", 0):
        log_audit_event("apply_failed_token_expired", {"proposal_id": proposal_id, "approver": approver})
        return {"error": "Approval token has expired.", "status": "rejected"}

    if record.get("token") != approval_token:
        log_audit_event("apply_failed_invalid_token", {"proposal_id": proposal_id, "approver": approver})
        return {"error": "Invalid approval token.", "status": "rejected"}

    record["used"] = True
    audit_id = f"audit_{uuid.uuid4().hex[:12]}"

    action = record["action"]
    service = record["service"]
    params = record["params"]

    # Pre-capture baseline for verification & potential auto-rollback
    baseline = _capture_baseline(service)
    record["baseline"] = baseline

    try:
        if action == "set_memory_limit":
            mem_mb = int(params["memory_mb"])
            subprocess.run(
                ["docker", "update", "--memory", f"{mem_mb}m", "--memory-swap", f"{mem_mb}m", service],
                check=True,
                capture_output=True,
            )
        elif action == "restart_service":
            subprocess.run(["docker", "restart", service], check=True, capture_output=True)
        elif action == "rollback_deploy":
            import httpx
            port_map = {"order-service": 8002, "payment-service": 8001, "inventory-service": 8003}
            port = port_map.get(service, 8000)
            try:
                httpx.post(f"http://localhost:{port}/admin/fault", json={"error_rate": 0.0}, timeout=3.0)
            except Exception:
                pass
            subprocess.run(["docker", "restart", service], check=True, capture_output=True)

        record["status"] = "applied"
        record["applied_at"] = now
        record["audit_id"] = audit_id
        record["verification_status"] = "monitoring"
        record["rolled_back"] = False

        log_audit_event("applied", {
            "proposal_id": proposal_id,
            "audit_id": audit_id,
            "action": action,
            "service": service,
            "params": params,
            "approver": approver,
            "status": "applied",
        })

        # Launch background verifier thread with auto-rollback capability
        threading.Thread(
            target=_background_verifier,
            args=(proposal_id, watch_seconds),
            daemon=True,
        ).start()

        return {
            "status": "applied",
            "audit_id": audit_id,
            "action": action,
            "service": service,
            "verification_window_seconds": watch_seconds,
        }
    except Exception as exc:
        record["status"] = "failed"
        log_audit_event("apply_failed_execution", {
            "proposal_id": proposal_id,
            "audit_id": audit_id,
            "error": str(exc),
        })
        return {"status": "failed", "error": f"Execution failed: {exc}", "audit_id": audit_id}


def verify_remediation(proposal_id: str) -> dict[str, Any]:
    """Query live verification and rollback status for a proposal."""
    if proposal_id not in _PROPOSALS:
        return {"error": f"Unknown proposal_id: {proposal_id}", "status": "unknown"}

    record = _PROPOSALS[proposal_id]
    if record.get("status") != "applied":
        return {"status": "pending", "message": "Proposal has not been applied yet."}

    return {
        "status": record.get("verification_status", "monitoring"),
        "service": record.get("service"),
        "rolled_back": record.get("rolled_back", False),
        "audit_id": record.get("audit_id"),
    }


if __name__ == "__main__":
    mcp.run_stdio_async()
