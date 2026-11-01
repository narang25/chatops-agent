"""
Unit tests for Kubernetes Backend (mcp_servers.kubernetes.backends.k8s_backend).
"""

from unittest.mock import MagicMock
import pytest

import mcp_servers.kubernetes.backends.k8s_backend as kb_module
from mcp_servers.kubernetes.backends.k8s_backend import (
    _to_contract_state,
    _parse_memory_mb,
    K8sBackend,
)


def test_parse_memory_mb():
    assert _parse_memory_mb("128Mi") == 128.0
    assert _parse_memory_mb("1Gi") == 1024.0
    assert _parse_memory_mb("64M") == 64.0


def test_to_contract_state_running():
    pod = MagicMock()
    pod.status.phase = "Running"
    cs = MagicMock()
    cs.state.waiting = None
    cs.state.terminated = None
    cs.state.running = MagicMock()
    pod.status.container_statuses = [cs]

    assert _to_contract_state(pod) == "running"


def test_to_contract_state_oom_killed():
    pod = MagicMock()
    pod.status.phase = "Running"
    cs = MagicMock()
    cs.state.waiting = None
    cs.state.terminated = MagicMock(reason="OOMKilled")
    pod.status.container_statuses = [cs]

    assert _to_contract_state(pod) == "oom_killed"


def test_to_contract_state_crash_loop():
    pod = MagicMock()
    pod.status.phase = "Running"
    cs = MagicMock()
    cs.state.waiting = MagicMock(reason="CrashLoopBackOff")
    cs.state.terminated = None
    pod.status.container_statuses = [cs]

    assert _to_contract_state(pod) == "restarting"


def test_k8s_backend_pod_status_and_events(monkeypatch):
    mock_config = MagicMock()
    mock_client = MagicMock()

    core_inst = MagicMock()
    mock_client.CoreV1Api.return_value = core_inst
    mock_client.AppsV1Api.return_value = MagicMock()

    # Set mock k8s client and config
    monkeypatch.setattr(kb_module, "_K8S_AVAILABLE", True)
    monkeypatch.setattr(kb_module, "k8s_config", mock_config, raising=False)
    monkeypatch.setattr(kb_module, "k8s_client", mock_client, raising=False)

    # Mock pod
    mock_pod = MagicMock()
    mock_pod.metadata.name = "payment-service-abc12"
    mock_pod.metadata.creation_timestamp = None
    mock_pod.status.phase = "Running"
    cs = MagicMock()
    cs.restart_count = 3
    cs.state.waiting = None
    cs.state.running = None
    cs.state.terminated = MagicMock(reason="OOMKilled", exit_code=137)
    cs.last_state.terminated = MagicMock(reason="OOMKilled", exit_code=137)
    mock_pod.status.container_statuses = [cs]
    mock_pod.status.conditions = [MagicMock(type="Ready", status="False")]

    core_inst.list_namespaced_pod.return_value.items = [mock_pod]

    backend = K8sBackend(namespace="chatops")
    status = backend.get_pod_status("payment-service")

    assert status["service"] == "payment-service"
    assert status["state"] == "oom_killed"
    assert status["oom_killed"] is True
    assert status["restart_count"] == 3
    assert status["exit_code"] == 137
    assert status["health"] == "unhealthy"
