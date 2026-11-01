"""
Unit tests for Remediation MCP Server, Safety Engine, Verification & Auto-Rollback (Tasks B20 & B22).
"""

import time
import pytest
from mcp_servers.remediation.server import (
    propose_remediation,
    apply_remediation,
    verify_remediation,
    check_policy,
    _PROPOSALS,
)


def test_policy_denies_unauthorized_service():
    allowed, msg = check_policy("restart_service", "postgres", {})
    assert not allowed
    assert "explicitly denied" in msg or "not permitted" in msg


def test_policy_denies_excessive_memory():
    allowed, msg = check_policy("set_memory_limit", "payment-service", {"memory_mb": 1024})
    assert not allowed
    assert "outside allowed range" in msg


def test_policy_allows_valid_request():
    allowed, msg = check_policy("set_memory_limit", "payment-service", {"memory_mb": 256})
    assert allowed


def test_propose_remediation_dry_run():
    res = propose_remediation("payment-service", "set_memory_limit", {"memory_mb": 256})
    assert "error" not in res
    assert res["requires_approval"] is True
    assert "proposal_id" in res
    assert "dry_run" in res
    assert len(res["dry_run"]["changes"]) > 0


def test_apply_remediation_requires_valid_token():
    res = propose_remediation("payment-service", "set_memory_limit", {"memory_mb": 256})
    p_id = res["proposal_id"]

    apply_res = apply_remediation(p_id, "invalid_token_123")
    assert apply_res["status"] == "rejected"
    assert "Invalid approval token" in apply_res["error"]


def test_apply_remediation_token_single_use(monkeypatch):
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)

    res = propose_remediation("order-service", "restart_service", {})
    p_id = res["proposal_id"]
    token = _PROPOSALS[p_id]["token"]

    apply_res1 = apply_remediation(p_id, token, approver="test_user", watch_seconds=1)
    assert apply_res1["status"] == "applied"

    apply_res2 = apply_remediation(p_id, token, approver="test_user", watch_seconds=1)
    assert apply_res2["status"] == "rejected"
    assert "already been used" in apply_res2["error"]


def test_apply_remediation_rejects_expired_token():
    res = propose_remediation("inventory-service", "restart_service", {})
    p_id = res["proposal_id"]
    token = _PROPOSALS[p_id]["token"]

    _PROPOSALS[p_id]["expires_at"] = time.time() - 10

    apply_res = apply_remediation(p_id, token, watch_seconds=1)
    assert apply_res["status"] == "rejected"
    assert "expired" in apply_res["error"]


# ── Verification & Auto-Rollback Tests (Task B22) ───────────────────────────

def test_verification_successful_when_healthy(monkeypatch):
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "mcp_servers.kubernetes.server.get_pod_status",
        lambda svc: {"state": "running", "restart_count": 0},
    )

    res = propose_remediation("payment-service", "set_memory_limit", {"memory_mb": 256})
    p_id = res["proposal_id"]
    token = _PROPOSALS[p_id]["token"]

    apply_remediation(p_id, token, approver="test_user", watch_seconds=1)

    time.sleep(1.5)

    v_res = verify_remediation(p_id)
    assert v_res["status"] == "improved"
    assert v_res["rolled_back"] is False


def test_verification_triggers_auto_rollback_when_worse(monkeypatch):
    executed_commands = []
    def fake_subprocess_run(cmd, *args, **kwargs):
        executed_commands.append(cmd)
        return None

    monkeypatch.setattr("subprocess.run", fake_subprocess_run)
    # Simulate service degraded / crashing post-remediation
    monkeypatch.setattr(
        "mcp_servers.kubernetes.server.get_pod_status",
        lambda svc: {"state": "oom_killed", "restart_count": 5},
    )

    res = propose_remediation("payment-service", "set_memory_limit", {"memory_mb": 256})
    p_id = res["proposal_id"]
    token = _PROPOSALS[p_id]["token"]

    apply_remediation(p_id, token, approver="test_user", watch_seconds=1)

    time.sleep(1.5)

    v_res = verify_remediation(p_id)
    assert v_res["status"] == "worse"
    assert v_res["rolled_back"] is True

    # Assert rollback docker update command was executed
    assert any("update" in cmd and "payment-service" in cmd for cmd in executed_commands)
