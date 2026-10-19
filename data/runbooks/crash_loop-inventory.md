---
title: "Crash Loop: Inventory Service Restarting Repeatedly"
failure_type: crash_loop
service: inventory-service
severity: critical
---

## Symptoms
- Container is in a restart loop: `docker ps` shows `Restarting (1) X seconds ago` or a high restart count.
- `get_pod_status` MCP tool returns `"state": "restarting"` and `restart_count` greater than 3.
- Application never reaches a healthy state; `GET /health` is unreachable between restarts.
- Structured log stream ends abruptly and repeats from the beginning each cycle:
  `{"timestamp": "2026-10-14T09:05:02.101Z", "service": "inventory-service", "level": "CRITICAL", "message": "Unhandled exception during startup: ...", "extra": {"exit_code": 1}}`
- Prometheus shows `app_requests_total{service="inventory-service"}` at zero or intermittent spikes.

## Likely cause
- Fatal startup exception: missing dependency (database, external service) prevents the app from initialising.
- Misconfigured environment variable causes an immediate `SystemExit` or `KeyError` at import time.
- Corrupted data in a mounted volume causes a crash on first read.
- Out-of-memory condition during startup (check `OOMKilled: true`) before the app is ready to serve.

## How to confirm
1. Check restart count and exit code:
   ```bash
   docker inspect inventory-service --format 'Restarts={{.RestartCount}} ExitCode={{.State.ExitCode}} OOM={{.State.OOMKilled}}'
   ```
2. Read the last crash log to find the root cause:
   ```bash
   docker logs --tail 100 inventory-service 2>&1 | grep -E "CRITICAL|ERROR|Traceback|Exception"
   ```
3. Try running the container interactively to see the exception at first-hand:
   ```bash
   docker run --rm --env-file infra/.env --entrypoint python \
     chatops-inventory-service -c "import app; app.create_app()"
   ```
4. Check if a dependent service (e.g. database) is running:
   ```bash
   docker ps --filter "name=postgres"
   ```

## Fix
1. Identify and fix the startup exception from the logs (see "How to confirm" above).
2. If the cause is a missing environment variable, update `infra/.env` and re-apply:
   ```bash
   docker compose -f infra/docker-compose.yml up -d --force-recreate inventory-service
   ```
3. If a corrupted volume is suspected, recreate it:
   ```bash
   docker compose -f infra/docker-compose.yml down -v inventory-service
   docker compose -f infra/docker-compose.yml up -d inventory-service
   ```
4. If the dependency (e.g. postgres) is missing, start it first:
   ```bash
   docker compose -f infra/docker-compose.yml up -d postgres
   # Wait for health check, then start the service
   docker compose -f infra/docker-compose.yml up -d inventory-service
   ```
5. Verify recovery:
   ```bash
   docker inspect inventory-service --format 'State={{.State.Status}}'
   curl -s http://localhost:8002/health | jq .
   ```

## Prevention
- Add a Docker `depends_on` with `condition: service_healthy` in `docker-compose.yml` to enforce startup ordering.
- Implement a startup readiness probe that retries dependency checks with exponential backoff before crashing.
- Set `restart: on-failure:5` (maximum 5 restarts) instead of `restart: always` to avoid infinite loops.
- Alert on `restart_count > 3` within a 5-minute window in Prometheus:
  ```promql
  increase(kube_pod_container_status_restarts_total[5m]) > 3
  ```
