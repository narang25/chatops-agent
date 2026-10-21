"""
Runtime backends for infrastructure MCP server.
"""

import os
from mcp_servers.kubernetes.backends.base import RuntimeBackend
from mcp_servers.kubernetes.backends.docker_backend import DockerBackend


def get_backend() -> RuntimeBackend:
    runtime = os.getenv("RUNTIME", "docker").lower()
    if runtime == "k8s" or runtime == "kubernetes":
        try:
            from mcp_servers.kubernetes.backends.k8s_backend import KubernetesBackend
            return KubernetesBackend()
        except ImportError:
            raise NotImplementedError("KubernetesBackend is scheduled for Week 3. Set RUNTIME=docker.")
    return DockerBackend()
