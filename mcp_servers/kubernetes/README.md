# Kubernetes & Container Infrastructure MCP Server

FastMCP server exposing container state, lifecycle events, structured JSON logs, and service discovery to the ChatOps AI agent via standard MCP stdio transport.

## Architecture

Implements a pluggable `RuntimeBackend` abstraction:
- **DockerBackend (Week 2, default):** Communicates with local Docker daemon via Docker Python SDK.
- **KubernetesBackend (Week 3):** Communicates with Kubernetes cluster (Minikube / kind) via official `kubernetes` client.

Selected via environment variable `RUNTIME=docker` (default) or `RUNTIME=k8s`.

## Tools Provided

### 1. `get_pod_status(service: str)`
Shape matches `contracts/mcp_tools.md`:
```json
{
  "service": "payment-service",
  "state": "running",
  "restart_count": 0,
  "exit_code": 0,
  "oom_killed": false,
  "health": "healthy",
  "started_at": "2026-10-21T10:00:00Z",
  "memory_limit_mb": 128
}
```
State mappings: `running`, `restarting`, `exited`, `oom_killed`, `unhealthy`, `not_found`.

### 2. `get_events(service: str, minutes: int = 15)`
Returns timestamped container lifecycle events (die, oom, kill, restart, health transition).

### 3. `get_logs(service: str, minutes: int = 10, level: str | None = None, limit: int = 100)`
Returns structured JSON logs filtered by time window and severity level matching `contracts/logs.md`.

### 4. `list_services()`
Discovers registered microservices and their active states.

## Running the Server

Over stdio (for MCP Inspector or Agent sub-processes):
```bash
python -m mcp_servers.kubernetes.server
```

## Running Unit Tests

```bash
pytest mcp_servers/kubernetes/test_server.py
```
