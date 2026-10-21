# Infrastructure MCP Tool Test Harness

Automated test suite asserting contract shapes, error resilience, and failure scenario detections across all 5 Person B MCP tools:
- `get_metrics`
- `get_pod_status`
- `get_events`
- `get_logs`
- `list_services`

## Running the Tests

Run via pytest:
```bash
pytest infra/tests/test_tools.py -v
```

This test suite runs both in local development and within the GitHub Actions CI pipeline on every Pull Request.
