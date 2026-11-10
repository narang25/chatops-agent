"""
Unit tests for Prometheus MCP Server & get_anomalies tool (Task B17).
"""

import pytest
from unittest.mock import patch, MagicMock
from mcp_servers.prometheus.server import (
    get_metrics,
    get_anomalies,
    METRIC_QUERY_TEMPLATES,
    VALID_SERVICES,
    _extract_log_patterns,
)


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


# ── get_anomalies tests (Task B17) ──────────────────────────────────────────

def test_get_anomalies_invalid_service():
    res = get_anomalies(service="invalid-service", minutes=10)
    assert "error" in res
    assert "Invalid service" in res["error"]


@patch("mcp_servers.prometheus.server._fetch_container_logs")
@patch("mcp_servers.prometheus.server._query_prometheus")
def test_get_anomalies_detects_metric_and_log_shift(mock_query, mock_logs):
    # Simulate baseline memory low (50MB), current memory high (120MB)
    def side_effect(promql, start, end, step):
        if "app_memory_bytes" in promql or "memory_usage_mb" in promql:
            if start < 1000:
                return [[500, 50.0]]
            return [[1200, 120.0]]
        return [[100, 1.0]]

    mock_query.side_effect = side_effect

    # Baseline logs vs current error logs
    mock_logs.side_effect = [
        # Baseline logs
        [{"message": "GET /health 200 OK", "level": "INFO", "timestamp": "2026-11-01T10:00:00Z"}],
        # Current logs with new OOM anomaly
        [
            {"message": "GET /health 200 OK", "level": "INFO", "timestamp": "2026-11-01T10:10:00Z"},
            {"message": "Memory limit exceeded: allocation failed for 10MB chunk", "level": "ERROR", "timestamp": "2026-11-01T10:12:00Z"},
            {"message": "Memory limit exceeded: allocation failed for 10MB chunk", "level": "ERROR", "timestamp": "2026-11-01T10:13:00Z"},
        ],
    ]

    res = get_anomalies(service="payment-service", minutes=10)

    assert "error" not in res
    assert res["service"] == "payment-service"
    assert res["window_minutes"] == 10
    assert "metric_anomalies" in res
    assert "log_anomalies" in res

    # Check that new log pattern is detected
    assert len(res["log_anomalies"]) >= 1
    assert any("Memory limit exceeded" in p["sample"] for p in res["log_anomalies"])


def test_drain3_log_pattern_clustering():
    sample_logs = [
        {"message": "Connected to database host=postgres port=5432 user=chatops", "level": "INFO", "timestamp": "T1"},
        {"message": "Connected to database host=postgres port=5432 user=chatops", "level": "INFO", "timestamp": "T2"},
        {"message": "Order 101 processed successfully in 45ms", "level": "INFO", "timestamp": "T3"},
        {"message": "Order 102 processed successfully in 52ms", "level": "INFO", "timestamp": "T4"},
    ]
    patterns = _extract_log_patterns(sample_logs)
    assert len(patterns) >= 1
