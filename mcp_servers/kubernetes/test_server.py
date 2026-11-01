"""
Unit tests for Kubernetes/Docker Infrastructure MCP Server & what_changed tool (Task B18).
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from mcp_servers.kubernetes.backends.docker_backend import DockerBackend
from mcp_servers.kubernetes.server import what_changed, set_backend


@pytest.fixture
def mock_docker_backend():
    with patch("docker.from_env") as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        backend = DockerBackend()
        backend.client = mock_client
        return backend, mock_client


def test_get_pod_status_running_healthy(mock_docker_backend):
    backend, mock_client = mock_docker_backend

    mock_container = MagicMock()
    mock_container.name = "payment-service"
    mock_container.attrs = {
        "State": {
            "Status": "running",
            "OOMKilled": False,
            "ExitCode": 0,
            "StartedAt": "2026-10-21T10:00:00Z",
            "Health": {"Status": "healthy"},
        },
        "RestartCount": 0,
        "HostConfig": {"Memory": 134217728},  # 128MB
    }
    mock_client.containers.list.return_value = [mock_container]

    res = backend.get_pod_status("payment-service")

    assert res["service"] == "payment-service"
    assert res["state"] == "running"
    assert res["restart_count"] == 0
    assert res["exit_code"] == 0
    assert res["oom_killed"] is False
    assert res["health"] == "healthy"
    assert res["memory_limit_mb"] == 128


def test_get_pod_status_oom_killed(mock_docker_backend):
    backend, mock_client = mock_docker_backend

    mock_container = MagicMock()
    mock_container.name = "payment-service"
    mock_container.attrs = {
        "State": {
            "Status": "exited",
            "OOMKilled": True,
            "ExitCode": 137,
            "StartedAt": "2026-10-21T10:00:00Z",
        },
        "RestartCount": 2,
        "HostConfig": {"Memory": 67108864},  # 64MB
    }
    mock_client.containers.list.return_value = [mock_container]

    res = backend.get_pod_status("payment-service")

    assert res["service"] == "payment-service"
    assert res["state"] == "oom_killed"
    assert res["restart_count"] == 2
    assert res["exit_code"] == 137
    assert res["oom_killed"] is True
    assert res["memory_limit_mb"] == 64


def test_get_pod_status_unhealthy(mock_docker_backend):
    backend, mock_client = mock_docker_backend

    mock_container = MagicMock()
    mock_container.name = "inventory-service"
    mock_container.attrs = {
        "State": {
            "Status": "running",
            "OOMKilled": False,
            "ExitCode": 0,
            "Health": {"Status": "unhealthy"},
        },
        "RestartCount": 0,
        "HostConfig": {"Memory": 134217728},
    }
    mock_client.containers.list.return_value = [mock_container]

    res = backend.get_pod_status("inventory-service")

    assert res["service"] == "inventory-service"
    assert res["state"] == "unhealthy"
    assert res["health"] == "unhealthy"


def test_get_pod_status_not_found(mock_docker_backend):
    backend, mock_client = mock_docker_backend
    mock_client.containers.list.return_value = []

    res = backend.get_pod_status("nonexistent-service")

    assert res["service"] == "nonexistent-service"
    assert res["state"] == "not_found"
    assert res["health"] == "none"


def test_get_logs_filtering_by_level(mock_docker_backend):
    backend, mock_client = mock_docker_backend

    mock_container = MagicMock()
    mock_container.name = "order-service"

    sample_logs = (
        '{"timestamp": "2026-10-21T10:01:00Z", "level": "INFO", "message": "Order created: id=1"}\n'
        'invalid raw log line to be ignored\n'
        '{"timestamp": "2026-10-21T10:02:00Z", "level": "ERROR", "message": "Payment connection refused"}\n'
        '{"timestamp": "2026-10-21T10:03:00Z", "level": "CRITICAL", "message": "Missing required env"}\n'
    )
    mock_container.logs.return_value = sample_logs.encode("utf-8")
    mock_client.containers.list.return_value = [mock_container]

    res = backend.get_logs("order-service", minutes=10, level="ERROR")

    assert res["service"] == "order-service"
    assert res["count"] == 1
    assert len(res["lines"]) == 1
    assert res["lines"][0]["level"] == "ERROR"
    assert res["lines"][0]["message"] == "Payment connection refused"


def test_list_services(mock_docker_backend):
    backend, mock_client = mock_docker_backend

    mock_container = MagicMock()
    mock_container.name = "payment-service"
    mock_container.attrs = {
        "State": {"Status": "running", "Health": {"Status": "healthy"}},
        "RestartCount": 0,
        "HostConfig": {},
    }
    mock_client.containers.list.return_value = [mock_container]

    res = backend.list_services()

    assert "services" in res
    assert len(res["services"]) == 3
    service_names = [s["name"] for s in res["services"]]
    assert "payment-service" in service_names
    assert "order-service" in service_names
    assert "inventory-service" in service_names


# ── what_changed tests (Task B18) ───────────────────────────────────────────

def test_what_changed_reads_deploy_events(mock_docker_backend, tmp_path):
    backend, mock_client = mock_docker_backend
    mock_client.containers.list.return_value = []

    # Mock DEPLOY_LOG_PATH
    fake_deploy_log = tmp_path / "deploy_events.jsonl"
    fake_event = {
        "timestamp": "2026-11-01T12:00:00Z",
        "service": "order-service",
        "action": "deploy",
        "image": "order-service:v2",
        "description": "Simulated deploy",
    }
    fake_deploy_log.write_text(json.dumps(fake_event) + "\n", encoding="utf-8")

    with patch("mcp_servers.kubernetes.backends.docker_backend.DEPLOY_LOG_PATH", fake_deploy_log):
        res = backend.what_changed(service="order-service", minutes=120)

    assert res["service"] == "order-service"
    assert "changes" in res
    assert any(c["type"] == "deploy" and c["source"] == "deploy_events_log" for c in res["changes"])


def test_what_changed_surfaces_docker_lifecycle_event(mock_docker_backend):
    backend, mock_client = mock_docker_backend

    mock_container = MagicMock()
    mock_container.id = "cont123"
    mock_container.name = "order-service"
    mock_client.containers.list.return_value = [mock_container]

    mock_client.events.return_value = [
        {
            "Action": "restart",
            "time": 1700000000,
            "Actor": {"Attributes": {"name": "order-service"}},
        }
    ]

    with patch("mcp_servers.kubernetes.backends.docker_backend.DEPLOY_LOG_PATH", MagicMock(exists=lambda: False)):
        res = backend.what_changed(service="order-service", minutes=60)

    assert res["service"] == "order-service"
    assert any(c["type"] == "container_restart" and c["source"] == "docker_events" for c in res["changes"])


def test_what_changed_handles_missing_github_token_cleanly(mock_docker_backend):
    backend, mock_client = mock_docker_backend
    mock_client.containers.list.return_value = []

    with patch.dict("os.environ", {}, clear=True):
        with patch("mcp_servers.kubernetes.backends.docker_backend.DEPLOY_LOG_PATH", MagicMock(exists=lambda: False)):
            res = backend.what_changed(service="payment-service", minutes=30)

    assert "error" not in res
    assert res["service"] == "payment-service"
    assert isinstance(res["changes"], list)
