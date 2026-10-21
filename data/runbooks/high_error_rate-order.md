---
title: "High Error Rate: Order Service Returning 5xx Errors"
failure_type: high_error_rate
service: order-service
severity: high
---

## Symptoms
- A significant portion of order requests return HTTP `500 Internal Server Error` or `502 Bad Gateway`.
- Structured logs show repeated unhandled exception traces:
  `{"timestamp": "2026-10-14T15:10:05.339Z", "service": "order-service", "level": "ERROR", "message": "Unhandled exception in POST /order", "extra": {"traceback": "ValueError: invalid literal for int() with base 10: ''"}}`
- Prometheus `app_errors_total{service="order-service"}` rate exceeds 5% of total requests.
- `http_request_duration_seconds{service="order-service", status="500"}` is non-zero.
- `get_metrics` MCP tool shows error count spiking relative to the request rate.

## Likely cause
- A bad code deployment introduced an unhandled exception on the hot path (e.g. type error, validation bug).
- A downstream service dependency (payment-service, inventory-service) returns unexpected responses causing cascade failures.
- A database schema migration mismatch: order-service code expects a column that does not exist yet.
- Malformed or unexpected request payloads from clients bypassing validation.
- Exhausted thread pool or connection pool causing requests to be rejected.

## How to confirm
1. Inspect recent application errors and tracebacks:
   ```bash
   docker logs --tail 200 order-service 2>&1 | grep -A 10 "ERROR\|Exception\|Traceback"
   ```
2. Calculate the real-time error rate in Prometheus:
   ```promql
   rate(app_errors_total{service="order-service"}[5m])
   rate(app_errors_total{service="order-service"}[5m]) /
     rate(app_requests_total{service="order-service"}[5m])
   ```
3. Test a minimal order request to reproduce the error:
   ```bash
   curl -v -X POST http://localhost:8003/order \
     -H "Content-Type: application/json" \
     -d '{"item_id": 1, "quantity": 2, "user_id": 42}'
   ```
4. Check whether downstream services are healthy:
   ```bash
   curl -s http://localhost:8001/health | jq .   # payment-service
   curl -s http://localhost:8002/health | jq .   # inventory-service
   ```
5. Review recent deployments or image tags:
   ```bash
   docker inspect order-service --format '{{.Config.Image}}'
   git log --oneline -10 -- sample_apps/order-service/
   ```

## Fix
1. If a bad deployment is the cause, roll back to the previous image:
   ```bash
   docker compose -f infra/docker-compose.yml stop order-service
   # Edit docker-compose.yml to pin the previous image tag, then:
   docker compose -f infra/docker-compose.yml up -d order-service
   ```
2. If a downstream dependency is unhealthy, fix it first (see `dependency_failure-order.md`).
3. If it is a validation or input-handling bug, apply a hotfix and redeploy:
   ```bash
   docker compose -f infra/docker-compose.yml build order-service
   docker compose -f infra/docker-compose.yml up -d order-service
   ```
4. If connection pool exhaustion is suspected, increase pool size and restart:
   ```bash
   # Set DB_POOL_SIZE env var in infra/.env, then:
   docker compose -f infra/docker-compose.yml up -d --force-recreate order-service
   ```
5. Verify the error rate drops:
   ```bash
   watch -n 2 'curl -s http://localhost:8003/health | jq .'
   ```

## Prevention
- Add structured exception logging with full tracebacks and request IDs on every unhandled error.
- Implement an API input validation layer (e.g. Pydantic) that returns `400 Bad Request` instead of `500` on bad input.
- Alert when `rate(app_errors_total[5m]) / rate(app_requests_total[5m]) > 0.05` for more than 1 minute.
- Use canary deployments to limit blast radius when releasing new order-service versions.
