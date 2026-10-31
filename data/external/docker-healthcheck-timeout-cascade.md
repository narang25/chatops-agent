---
title: "Health Check Command Timeout: Restart Cascade in Docker Compose"
failure_type: "health_check_failure"
source_type: "external_doc"
source_url: "https://docs.docker.com/engine/reference/builder/#healthcheck"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Healthy containers under moderate load are suddenly marked `unhealthy` and restarted repeatedly by Docker or orchestration layer, creating a cascading outage.

## Likely cause
`HEALTHCHECK` command timeout is too short (e.g. `timeout: 3s`) while probing an endpoint that does database queries. Under load, query latency spikes beyond 3s, causing health check to fail 3 consecutive times.

## How to confirm
Inspect container health logs:
`docker inspect <container> --format '{{json .State.Health}}' | jq .`
Check duration of recent health checks in `Log` array.

## Fix
1. Make health check endpoint lightweight (avoid database queries in `/healthz` liveness; keep deep checks in `/readyz`).
2. Increase timeout and retries in docker-compose.yml:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 15s
  timeout: 10s
  retries: 5
  start_period: 30s
```
