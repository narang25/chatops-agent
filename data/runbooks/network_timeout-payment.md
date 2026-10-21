---
title: "Network Timeout: Payment Service Downstream Calls Timing Out"
failure_type: network_timeout
service: payment-service
severity: high
---

## Symptoms
- Payment API returns HTTP `504 Gateway Timeout` or `503 Service Unavailable`.
- Application logs show repeated read timeout errors on outbound calls:
  `{"timestamp": "2026-10-14T12:33:55.820Z", "service": "payment-service", "level": "ERROR", "message": "Timeout calling fraud-check service after 3s", "extra": {"url": "http://fraud-check:8080/verify", "request_id": "xyz789"}}`
- `http_request_duration_seconds{service="payment-service", endpoint="/pay"}` p95 latency exceeds 3000ms.
- `app_errors_total{service="payment-service"}` counter increases while throughput drops.
- `get_events` MCP tool shows repeated `NetworkError` or `Timeout` events for payment-service.

## Likely cause
- A downstream dependency (fraud-check, notification service, external payment gateway) is slow or unreachable.
- Docker network congestion or a misconfigured `chatops-net` network causing packet loss.
- DNS resolution failure inside the container network preventing hostname lookup.
- Firewall rules or security group changes blocking egress on the required port.
- The upstream service is overloaded (high CPU or memory pressure), causing slow responses.

## How to confirm
1. Measure round-trip time to the downstream service from inside payment-service:
   ```bash
   docker exec payment-service curl -v --max-time 5 http://fraud-check:8080/health
   ```
2. Check DNS resolution works correctly within the container network:
   ```bash
   docker exec payment-service nslookup fraud-check
   ```
3. Inspect Docker network routing and connected containers:
   ```bash
   docker network inspect chatops-net
   docker network ls
   ```
4. Query Prometheus for downstream latency and error rate:
   ```promql
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="payment-service"}[5m]))
   rate(app_errors_total{service="payment-service"}[5m])
   ```
5. Check whether the downstream container is healthy:
   ```bash
   docker inspect fraud-check --format 'Status={{.State.Status}} Health={{.State.Health.Status}}'
   ```

## Fix
1. If the downstream service is down, restart it:
   ```bash
   docker compose -f infra/docker-compose.yml restart fraud-check
   ```
2. If it is a transient network partition, reconnect the container to the network:
   ```bash
   docker network disconnect chatops-net payment-service
   docker network connect chatops-net payment-service
   ```
3. If DNS is the issue, recreate the container (DNS config is set at container start):
   ```bash
   docker compose -f infra/docker-compose.yml up -d --force-recreate payment-service
   ```
4. Use the circuit-breaker endpoint to temporarily bypass the failing downstream:
   ```bash
   curl -X POST http://localhost:8001/admin/circuit-breaker/open -d '{"service": "fraud-check"}'
   ```
5. Verify recovery:
   ```bash
   curl -X POST http://localhost:8001/pay \
     -H "Content-Type: application/json" \
     -d '{"order_id": 100, "amount": 25.0}'
   ```

## Prevention
- Implement client-side timeouts and retries with exponential backoff on all outbound HTTP calls.
- Deploy a circuit breaker (e.g. `tenacity`, `pybreaker`) to fail fast when a downstream is degraded.
- Alert when `histogram_quantile(0.95, ...) > 2` seconds for more than 2 minutes.
- Add a `healthcheck` to the downstream container so Docker restarts it automatically on failure.
