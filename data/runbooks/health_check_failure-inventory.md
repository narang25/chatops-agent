---
title: "Health Check Failure: Inventory Service Returning 500"
failure_type: health_check_failure
service: inventory-service
severity: high
---

## Symptoms
- Health probe `GET /health` returns HTTP status code `500 Internal Server Error`.
- Docker reports container status as `unhealthy`.
- Logs show recurring warning messages:
  `{"timestamp": "2026-10-13T11:46:16.555Z", "service": "inventory-service", "level": "WARNING", "message": "Health check failed (fault injected)"}`
- Prometheus metric `app_up{service="inventory-service"} == 0` or alert `ServiceUnhealthy` fires.

## Likely cause
- Fault injection toggle `health_fail` is activated via administrative endpoint (`/admin/fault`).
- Database connectivity failure or connection pool exhaustion preventing the health endpoint from pinging Postgres.
- Disk or resource exhaustion causing internal readiness check failure.

## How to confirm
1. Direct HTTP request to the health endpoint:
   ```bash
   curl -i http://localhost:8003/health
   ```
2. Check Docker container health status:
   ```bash
   docker inspect inventory-service --format '{{.State.Health.Status}} (FailingStreak={{.State.Health.FailingStreak}})'
   ```
3. Inspect the fault toggle state via admin endpoint:
   ```bash
   curl -s http://localhost:8003/admin/fault
   ```

## Fix
1. If caused by simulated fault injection, reset the toggle:
   ```bash
   curl -X POST http://localhost:8003/admin/fault -H "Content-Type: application/json" -d '{"health_fail": false}'
   ```
   Or run the automated restore script:
   ```bash
   python infra/failures/restore.py
   ```
2. If caused by database disconnect, check Postgres status and restart if needed:
   ```bash
   docker compose -f infra/docker-compose.yml restart postgres inventory-service
   ```
3. Verify that `/health` returns HTTP 200:
   ```bash
   curl -f http://localhost:8003/health
   ```

## Prevention
- Separate shallow liveness checks (process alive) from deep readiness checks (database connectivity).
- Set sensible probe thresholds (`interval: 5s`, `retries: 3`, `start_period: 10s`) to avoid flapping.
- Protect `/admin/fault` endpoints with strict role-based access control or disable in production.
