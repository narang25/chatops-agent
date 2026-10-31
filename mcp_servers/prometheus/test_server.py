"""
Unit tests for Prometheus MCP Server.
Tests validation, metric whitelisting, response shaping, and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from mcp_servers.prometheus.server import get_metrics, METRIC_QUERY_TEMPLATES, VALID_SERVICES


def test_invalid_service_returns_error():
    res = get_metrics(service="unknown-service", metric="app_up")
    assert "error" in res
    assert "Invalid service" in res["error"]


def test_invalid_metric_returns_error():
    res = get_metrics(service="payment-service", metric="malicious_query_drop_table")
    assert "error" in res
    assert "Invalid metric" in res["error"]


@patch("mcp_servers.prometheus.server._query_prometheus")
def test_valid_metric_query_success(mock_query):
    # Mock samples returned from Prometheus
    mock_query.return_value = [
        [1700000000, 10.0],
        [1700000015, 15.5],
        [1700000030, 20.0],
    ]

    res = get_metrics(service="payment-service", metric="app_memory_bytes", minutes=5)

    assert "error" not in res
    assert res["service"] == "payment-service"
    assert res["metric"] == "app_memory_bytes"
    assert res["window_minutes"] == 5
    assert res["latest"] == 20.0
    assert res["min"] == 10.0
    assert res["max"] == 20.0
    assert len(res["samples"]) == 3
    assert res["samples"][0] == [1700000000, 10.0]


@patch("mcp_servers.prometheus.server._query_prometheus")
def test_empty_metric_samples_returns_nulls(mock_query):
    mock_query.return_value = []

    res = get_metrics(service="order-service", metric="app_errors_total", minutes=10)

    assert "error" not in res
    assert res["service"] == "order-service"
    assert res["latest"] is None
    assert res["min"] is None
    assert res["max"] is None
    assert res["samples"] == []


@patch("mcp_servers.prometheus.server._query_prometheus")
def test_prometheus_connection_failure_handled_gracefully(mock_query):
    mock_query.side_effect = Exception("Connection refused on port 9090")

    res = get_metrics(service="inventory-service", metric="app_up", minutes=5)

    assert "error" in res
    assert "Prometheus query failed" in res["error"]
