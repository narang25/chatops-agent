"""
Automated Test Harness for ChatOps MCP Infrastructure Tools.
Validates that get_metrics, get_pod_status, get_events, get_logs, and list_services
return accurate telemetry under baseline and failure conditions.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Ensure repo root is in python path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mcp_servers.prometheus.server import get_metrics
from mcp_servers.kubernetes.server import (
    get_pod_status,
    get_events,
    get_logs,
    list_services,
    set_backend,
)
from mcp_servers.kubernetes.backends.docker_backend import DockerBackend


@pytest.fixture(autouse=True)
def reset_mcp_backend():
    yield
    set_backend(None)


def create_mock_docker_backend(mock_containers=None):
    backend = DockerBackend()
    backend.client = MagicMock()
    backend.client.containers.list.return_value = mock_containers or []
    set_backend(backend)
    return backend


class TestToolContracts:
    """Verifies that all 5 tools return the exact schema matching contracts/mcp_tools.md."""

    def test_get_metrics_contract_shape(self):
        with patch("mcp_servers.prometheus.server._query_prometheus") as mock_query:
            mock_query.return_value = [[1700000000, 100.0], [1700000015, 120.0]]
            res = get_metrics("payment-service", "app_memory_bytes", minutes=5)

            assert "service" in res
            assert "metric" in res
            assert "window_minutes" in res
            assert "latest" in res
            assert "min" in res
            assert "max" in res
            assert "samples" in res
            assert res["latest"] == 120.0

    def test_get_pod_status_contract_shape(self):
        mock_c = MagicMock()
        mock_c.name = "payment-service"
        mock_c.attrs = {
            "State": {
                "Status": "running",
                "OOMKilled": False,
                "ExitCode": 0,
                "StartedAt": "2026-10-21T10:00:00Z",
                "Health": {"Status": "healthy"},
            },
            "RestartCount": 0,
            "HostConfig": {"Memory": 134217728},
        }
        create_mock_docker_backend([mock_c])

        res = get_pod_status("payment-service")
        assert res["service"] == "payment-service"
        assert res["state"] == "running"
        assert res["restart_count"] == 0
        assert res["exit_code"] == 0
        assert res["oom_killed"] is False
        assert res["health"] == "healthy"
        assert res["started_at"] is not None
        assert res["memory_limit_mb"] == 128

    def test_get_events_contract_shape(self):
        mock_c = MagicMock()
        mock_c.name = "order-service"
        mock_c.attrs = {"State": {"Status": "running", "StartedAt": "2026-10-21T10:00:00Z"}}
        create_mock_docker_backend([mock_c])

        res = get_events("order-service", minutes=15)
        assert res["service"] == "order-service"
        assert "events" in res
        assert isinstance(res["events"], list)
        if res["events"]:
            ev = res["events"][0]
            assert "timestamp" in ev
            assert "type" in ev
            assert "reason" in ev
            assert "message" in ev

    def test_get_logs_contract_shape(self):
        mock_c = MagicMock()
        mock_c.name = "inventory-service"
        mock_c.logs.return_value = (
            b'{"timestamp": "2026-10-21T10:00:00Z", "level": "INFO", "message": "Stock check: widget"}\n'
        )
        create_mock_docker_backend([mock_c])

        res = get_logs("inventory-service", minutes=10)
        assert res["service"] == "inventory-service"
        assert res["count"] == 1
        assert len(res["lines"]) == 1
        line = res["lines"][0]
        assert line["timestamp"] == "2026-10-21T10:00:00Z"
        assert line["level"] == "INFO"
        assert line["message"] == "Stock check: widget"

    def test_list_services_contract_shape(self):
        create_mock_docker_backend([])

        res = list_services()
        assert "services" in res
        assert len(res["services"]) == 3
        for item in res["services"]:
            assert "name" in item
            assert "state" in item


class TestScenarioDiagnostics:
    """Verifies that MCP tools observe expected signatures for each failure scenario."""

    def test_oom_scenario_detection(self):
        """OOM: get_pod_status reports oom_killed=true or exit_code 137."""
        mock_c = MagicMock()
        mock_c.name = "payment-service"
        mock_c.attrs = {
            "State": {
                "Status": "exited",
                "OOMKilled": True,
                "ExitCode": 137,
            },
            "RestartCount": 1,
            "HostConfig": {"Memory": 67108864},
        }
        create_mock_docker_backend([mock_c])

        status = get_pod_status("payment-service")
        assert status["oom_killed"] is True
        assert status["exit_code"] == 137
        assert status["state"] == "oom_killed"

    def test_bad_env_scenario_detection(self):
        """Bad Config: get_pod_status reports exited, get_logs reports CRITICAL log."""
        mock_c = MagicMock()
        mock_c.name = "order-service"
        mock_c.attrs = {
            "State": {
                "Status": "exited",
                "ExitCode": 1,
                "OOMKilled": False,
            },
            "RestartCount": 0,
            "HostConfig": {},
        }
        mock_c.logs.return_value = (
            b'{"timestamp": "2026-10-21T10:00:00Z", "level": "CRITICAL", "message": "PAYMENT_SERVICE_URL required"}\n'
        )
        create_mock_docker_backend([mock_c])

        status = get_pod_status("order-service")
        logs = get_logs("order-service", level="CRITICAL")

        assert status["exit_code"] == 1
        assert status["state"] == "exited"
        assert logs["count"] == 1
        assert "PAYMENT_SERVICE_URL" in logs["lines"][0]["message"]

    def test_health_fail_scenario_detection(self):
        """Health Failure: get_pod_status reports unhealthy."""
        mock_c = MagicMock()
        mock_c.name = "inventory-service"
        mock_c.attrs = {
            "State": {
                "Status": "running",
                "Health": {"Status": "unhealthy"},
            },
            "RestartCount": 0,
            "HostConfig": {},
        }
        create_mock_docker_backend([mock_c])

        status = get_pod_status("inventory-service")
        assert status["health"] == "unhealthy"
        assert status["state"] == "unhealthy"
