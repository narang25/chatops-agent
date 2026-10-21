---
title: "Database Connection Timeout: Payment Service Unable to Reach Postgres"
failure_type: db_timeout
service: payment-service
severity: high
---

## Symptoms
- Payment requests fail with HTTP `500 Internal Server Error`.
- Structured application logs display database connection timeout:
  `{"timestamp": "2026-10-12T10:15:30.123Z", "service": "payment-service", "level": "ERROR", "message": "Database connection timed out after 5s", "extra": {"request_id": "abc123"}}`
- Prometheus error counter `app_errors_total{service="payment-service"}` spikes.
- Latency histogram `http_request_duration_seconds{service="payment-service"}` shifts to >5s (timeout window).

## Likely cause
- The PostgreSQL database container (`postgres`) is stopped, crashed, or restarting.
- Database connection pool is saturated by unclosed transactions or slow queries.
- Network partition between the application container and the PostgreSQL container on the Docker network `chatops-net`.

## How to confirm
1. Check if the PostgreSQL container is running and healthy:
   ```bash
   docker ps --filter "name=postgres"
   docker inspect postgres --format 'Status={{.State.Status}} Health={{.State.Health.Status}}'
   ```
2. Test network connectivity and port accessibility from within `payment-service`:
   ```bash
   docker exec -it payment-service nc -zv postgres 5432
   ```
3. Check PostgreSQL server logs for errors or max connection limits:
   ```bash
   docker logs --tail 50 postgres
   ```

## Fix
1. If the database container is stopped or unhealthy, restart it:
   ```bash
   docker compose -f infra/docker-compose.yml restart postgres
   ```
2. Wait for PostgreSQL readiness (health check passes):
   ```bash
   docker exec postgres pg_isready -U chatops -d chatops
   ```
3. Restart `payment-service` to re-establish connection pools:
   ```bash
   docker compose -f infra/docker-compose.yml restart payment-service
   ```
4. Verify by submitting a test payment:
   ```bash
   curl -X POST http://localhost:8001/pay -H "Content-Type: application/json" -d '{"order_id": 999, "amount": 10.0}'
   ```

## Prevention
- Configure connection pool recycling (`pool_recycle=300`) and sensible checkout timeouts (`pool_timeout=5`).
- Ensure Postgres connection limits (`max_connections=200`) accommodate all replica pools.
- Deploy database health checks with auto-healing and persistent volume backups.
