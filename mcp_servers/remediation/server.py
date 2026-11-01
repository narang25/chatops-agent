"""
Remediation MCP Server & Safety Engine (Task B20).

Architecture & Safety Rules:
- Propose-only for Agent: The agent client is ONLY registered with `propose_remediation`.
- Apply is gated: `apply_remediation` requires a single-use, time-bound approval token
  issued solely through the interactive Slack approval interface or authorized human callers.
- Policy-Enforced: Evaluates requests against `infra/remediation_policy.yaml`.
- Audit Log: Every proposal, approval, rejection, and execution is recorded in `data/audit_log.jsonl`.
"""

import json
import os
import subprocess
import sys
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

# In-memory storage for active proposals and tokens
# Format: {proposal_id: {data..., "token": str, "expires_at": float, "used": bool}}
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


# ── FastMCP Server Instance ───────────────────────────────────────────────────

mcp = MCPServer(
    name="chatops-remediation",
    version="1.0.0",
    description="Safety-gated remediation proposal and execution engine.",
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

    # Policy validation
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

    # Dry-run analysis
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

    # Note: approval_token is retained internally; caller receives proposal confirmation
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


def apply_remediation(proposal_id: str, approval_token: str, approver: str = "slack_user") -> dict[str, Any]:
    """
    Execute a previously approved proposal.
    GATED: Rejects invalid, expired, or reused tokens.
    """
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

    # Mark token used immediately to prevent race conditions
    record["used"] = True
    audit_id = f"audit_{uuid.uuid4().hex[:12]}"

    action = record["action"]
    service = record["service"]
    params = record["params"]

    # Execute action via Docker
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
            # Clear error rate fault on service
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

        log_audit_event("applied", {
            "proposal_id": proposal_id,
            "audit_id": audit_id,
            "action": action,
            "service": service,
            "params": params,
            "approver": approver,
            "status": "applied",
        })

        return {
            "status": "applied",
            "audit_id": audit_id,
            "action": action,
            "service": service,
            "verification_window_minutes": 3,
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
    """Verify outcome of applied remediation."""
    if proposal_id not in _PROPOSALS:
        return {"error": f"Unknown proposal_id: {proposal_id}", "status": "unknown"}

    record = _PROPOSALS[proposal_id]
    if record.get("status") != "applied":
        return {"status": "pending", "message": "Proposal has not been applied yet."}

    service = record["service"]
    # Quick probe: check health and errors
    try:
        from mcp_servers.kubernetes.server import get_pod_status
        status = get_pod_status(service)
        state = status.get("state")
        if state in ["running"]:
            return {"status": "improved", "service": service, "current_state": state, "rolled_back": False}
        elif state in ["oom_killed", "exited", "restarting"]:
            return {"status": "worse", "service": service, "current_state": state, "rolled_back": False}
        return {"status": "unchanged", "service": service, "current_state": state, "rolled_back": False}
    except Exception as e:
        return {"status": "pending", "error": str(e), "rolled_back": False}


if __name__ == "__main__":
    mcp.run_stdio_async()
