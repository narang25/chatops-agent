---
title: "Downstream Dependency Failure: Order Service Cannot Reach Payment Service"
failure_type: dependency_failure
service: order-service
severity: high
---

## Symptoms
- Order creation endpoint `POST /orders` fails with HTTP `502 Bad Gateway` or `500 Internal Server Error`.
- Order service logs show HTTP client connection errors:
  `{"timestamp": "2026-10-14T08:20:10.001Z", "service": "order-service", "level": "ERROR", "message": "Failed to call payment-service: ConnectError [Errno 111] Connection refused"}`
- Metric `app_errors_total{service="order-service"}` increases while `order-service` itself reports `app_up == 1`.
- Downstream service `payment-service` has `app_up == 0` or missing metrics.

## Likely cause
- The downstream dependency `payment-service` has crashed, is restarting, or is unresponsive.
- Network disconnection or DNS resolution failure within Docker bridge network `chatops-net`.
- `PAYMENT_SERVICE_URL` points to an incorrect host or port.

## How to confirm
1. Check status of downstream containers:
   ```bash
   docker ps -a --filter "name=payment-service"
   ```
2. Verify HTTP reachability from inside `order-service` to `payment-service`:
   ```bash
   docker exec -it order-service curl -i http://payment-service:8001/health
   ```
3. Check Prometheus metrics for both services:
   ```promql
   app_up{service=~"order-service|payment-service"}
   rate(http_requests_total{status=~"5.."}[2m])
   ```

## Fix
1. Inspect and restart the failing downstream dependency:
   ```bash
   docker logs --tail 30 payment-service
   docker compose -f infra/docker-compose.yml restart payment-service
   ```
2. If `payment-service` is in a crash loop (e.g. OOM or bad config), follow the relevant runbook:
   - For memory issues, see `data/runbooks/out_of_memory-payment.md`.
   - For database issues, see `data/runbooks/db_timeout-payment.md`.
3. Once `payment-service` `/health` returns 200, test end-to-end order flow:
   ```bash
   curl -X POST http://localhost:8002/orders -H "Content-Type: application/json" -d '{"item": "widget", "quantity": 1, "amount": 25.0}'
   ```

## Prevention
- Implement circuit breakers and graceful retry with exponential backoff in `order-service`.
- Return degraded fallback responses or queue orders asynchronously when downstream payments are transiently down.
- Add synthetic health checks covering cross-service communication.
