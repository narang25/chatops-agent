"""
Unit tests for Remediation MCP Server & Safety Engine (Task B20).
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

    # Attempt with incorrect token
    apply_res = apply_remediation(p_id, "invalid_token_123")
    assert apply_res["status"] == "rejected"
    assert "Invalid approval token" in apply_res["error"]


def test_apply_remediation_token_single_use(monkeypatch):
    # Mock subprocess.run to avoid calling real docker
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)

    res = propose_remediation("order-service", "restart_service", {})
    p_id = res["proposal_id"]
    token = _PROPOSALS[p_id]["token"]

    # First apply succeeds
    apply_res1 = apply_remediation(p_id, token, approver="test_user")
    assert apply_res1["status"] == "applied"

    # Second apply with same token fails
    apply_res2 = apply_remediation(p_id, token, approver="test_user")
    assert apply_res2["status"] == "rejected"
    assert "already been used" in apply_res2["error"]


def test_apply_remediation_rejects_expired_token():
    res = propose_remediation("inventory-service", "restart_service", {})
    p_id = res["proposal_id"]
    token = _PROPOSALS[p_id]["token"]

    # Force expiration
    _PROPOSALS[p_id]["expires_at"] = time.time() - 10

    apply_res = apply_remediation(p_id, token)
    assert apply_res["status"] == "rejected"
    assert "expired" in apply_res["error"]
