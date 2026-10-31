# Prometheus Metrics MCP Server

FastMCP server exposing Prometheus time-series metrics to the ChatOps AI agent via the standard MCP stdio transport.

## Tool Provided

### `get_metrics(service, metric, minutes=5)`
Shape matches `contracts/mcp_tools.md`:
```json
{
  "service": "payment-service",
  "metric": "app_memory_bytes",
  "window_minutes": 5,
  "latest": 52428800.0,
  "min": 48234496.0,
  "max": 52428800.0,
  "samples": [
    [1791891500, 48234496.0],
    [1791891515, 52428800.0]
  ]
}
```

## Whitelisted Metrics

To prevent arbitrary PromQL injection and ensure reliability, only pre-configured queries are permitted:

- **Application metrics:** `http_requests_total`, `http_request_duration_seconds`, `app_errors_total`, `app_memory_bytes`, `app_up`
- **cAdvisor container metrics:** `container_memory_usage_bytes`, `container_spec_memory_limit_bytes`, `container_cpu_usage_seconds_total`
- **Semantic aliases:** `request_rate`, `error_rate`, `cpu_usage`, `memory_usage_mb`, `latency_p95_ms`, `latency_p99_ms`

## Running the Server

Over stdio (for MCP Inspector or Agent sub-processes):
```bash
python -m mcp_servers.prometheus.server
```

## Running Unit Tests

```bash
pytest mcp_servers/prometheus/test_server.py
```
