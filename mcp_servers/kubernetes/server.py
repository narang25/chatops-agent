"""
Kubernetes & Container Infrastructure MCP Server (mcp v2 / MCPServer API).

Exposes tools:
    get_pod_status(service)
    get_events(service, minutes=15)
    get_logs(service, minutes=10, level=None, limit=100)
    list_services()

Shapes match contracts/mcp_tools.md.

Run via stdio transport:
    python -m mcp_servers.kubernetes.server
"""

import sys
from pathlib import Path
from typing import Any

# Ensure project root is importable regardless of cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.mcpserver import MCPServer
from mcp_servers.kubernetes.backends import get_backend

mcp = MCPServer(
    name="chatops-kubernetes",
    version="1.0.0",
    description="Container and pod infrastructure inspection MCP server for ChatOps microservices.",
)

_backend = None


def _get_active_backend():
    global _backend
    if _backend is None:
        _backend = get_backend()
    return _backend


@mcp.tool(
    description=(
        "Get current container or pod status for a microservice. "
        "Returns state (running, restarting, exited, oom_killed, unhealthy, not_found), "
        "restart_count, exit_code, oom_killed, health, started_at, and memory_limit_mb."
    )
)
def get_pod_status(service: str) -> dict[str, Any]:
    """
    Get current container/pod status for a service.

    Args:
        service: Name of the microservice ('payment-service' | 'order-service' | 'inventory-service')
    """
    try:
        return _get_active_backend().get_pod_status(service)
    except Exception as exc:
        return {"error": f"get_pod_status failed: {exc}"}


@mcp.tool(
    description=(
        "Get recent lifecycle events for a microservice container or pod. "
        "Returns a timestamped list of events including restarts, OOM kills, "
        "and health check transitions."
    )
)
def get_events(service: str, minutes: int = 15) -> dict[str, Any]:
    """
    Get recent lifecycle events for a service.

    Args:
        service: Name of the microservice
        minutes: Time window lookback in minutes (default 15)
    """
    try:
        return _get_active_backend().get_events(service, minutes=minutes)
    except Exception as exc:
        return {"error": f"get_events failed: {exc}"}


@mcp.tool(
    description=(
        "Fetch recent structured JSON application logs for a microservice. "
        "Can be filtered by log level (INFO, WARNING, ERROR, CRITICAL). "
        "Returns chronological list of log entries matching contracts/logs.md."
    )
)
def get_logs(
    service: str,
    minutes: int = 10,
    level: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Get structured JSON log lines for a service.

    Args:
        service: Name of the microservice
        minutes: Lookback time window in minutes (default 10)
        level: Optional log level filter ('INFO' | 'WARNING' | 'ERROR' | 'CRITICAL')
        limit: Maximum number of log lines to return (default 100)
    """
    try:
        return _get_active_backend().get_logs(
            service=service, minutes=minutes, level=level, limit=limit
        )
    except Exception as exc:
        return {"error": f"get_logs failed: {exc}"}


@mcp.tool(
    description=(
        "List all registered microservices in the ChatOps architecture and their "
        "current runtime state."
    )
)
def list_services() -> dict[str, Any]:
    """
    List all registered microservices and their current state.
    """
    try:
        return _get_active_backend().list_services()
    except Exception as exc:
        return {"error": f"list_services failed: {exc}"}


if __name__ == "__main__":
    mcp.run_stdio_async()
