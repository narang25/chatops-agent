"""
Runtime backends for infrastructure MCP server.

Set environment variable RUNTIME=docker (default) or RUNTIME=k8s to switch.
"""

import os

from mcp_servers.kubernetes.backends.base import RuntimeBackend
from mcp_servers.kubernetes.backends.docker_backend import DockerBackend


def get_backend() -> RuntimeBackend:
    runtime = os.getenv("RUNTIME", "docker").lower()
    if runtime in ("k8s", "kubernetes"):
        from mcp_servers.kubernetes.backends.k8s_backend import K8sBackend
        return K8sBackend()
    return DockerBackend()
