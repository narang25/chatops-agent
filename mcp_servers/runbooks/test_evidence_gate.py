"""
Unit tests for the Evidence-First Code Gate (Task T2).
"""

from __future__ import annotations

import pytest

from mcp_servers.runbooks.evidence_gate import (
    check_evidence_gate,
    record_evidence,
    reset_evidence,
)
from mcp_servers.runbooks.server import search_runbooks


@pytest.fixture(autouse=True)
def clean_evidence():
    """Ensure clean evidence trace before and after every test."""
    reset_evidence()
    yield
    reset_evidence()


def test_search_runbooks_with_no_evidence_returns_error():
    """T2 core requirement: calling search_runbooks first with no evidence returns error."""
    res = search_runbooks("payment-service container killed out of memory")
    assert "error" in res
    assert "gather evidence first" in res["error"]
    assert "payment-service" in res["error"]


def test_search_runbooks_missing_logs_returns_error():
    """Gate blocks search when only pod status was collected (missing logs)."""
    record_evidence("get_pod_status", service="payment-service")
    res = search_runbooks("payment-service container killed out of memory")
    assert "error" in res
    assert "gather evidence first" in res["error"]
    assert "missing: get_logs for payment-service" in res["error"]


def test_search_runbooks_missing_status_returns_error():
    """Gate blocks search when only logs were collected (missing pod status)."""
    record_evidence("get_logs", service="payment-service")
    res = search_runbooks("payment-service container killed out of memory")
    assert "error" in res
    assert "gather evidence first" in res["error"]
    assert "missing: get_pod_status for payment-service" in res["error"]


def test_search_runbooks_with_both_status_and_logs_succeeds():
    """Gate opens when both pod status and logs for the service are present."""
    record_evidence("get_pod_status", service="payment-service")
    record_evidence("get_logs", service="payment-service")
    res = search_runbooks("payment-service container killed out of memory")
    assert "error" not in res
    assert "results" in res
    assert isinstance(res["results"], list)


def test_search_runbooks_unspecified_service_requires_list_services():
    """When query names no specific service, list_services must be in trace."""
    # No service named, no list_services in trace -> error
    res = search_runbooks("something strange is happening in the cluster")
    assert "error" in res
    assert "gather evidence first" in res["error"]
    assert "list_services" in res["error"]

    # Now call list_services -> passes
    record_evidence("list_services")
    res2 = search_runbooks("something strange is happening in the cluster")
    assert "error" not in res2
    assert "results" in res2


def test_search_runbooks_bypass_flag():
    """enforce_evidence=False explicitly bypasses the gate for offline evaluation."""
    res = search_runbooks("container killed out of memory", enforce_evidence=False)
    assert "error" not in res
    assert "results" in res

