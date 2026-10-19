---
title: "CPU Saturation: High Latency and Event Loop Throttling"
failure_type: cpu_saturation
service: any
severity: medium
---

## Symptoms
- Severe latency degradation across HTTP endpoints (p95 / p99 latency spikes above 2000ms).
- Client requests timing out or experiencing socket hang-ups.
- Service logs report event loop or worker thread lag:
  `{"timestamp": "2026-10-15T14:10:05.120Z", "service": "payment-service", "level": "WARNING", "message": "Event loop blocked for 450ms; slow request processing"}`
- Prometheus cAdvisor metrics show container CPU utilization pinned near limits:
  `rate(container_cpu_usage_seconds_total[1m])`

## Likely cause
- Heavy computational work or unindexed database queries executing synchronously on the main thread.
- Traffic burst exceeding single-core CPU quota allocated in Docker Compose.
- Inefficient serialization or infinite regex evaluation on incoming payloads.

## How to confirm
1. Check CPU throttling and active usage via Docker stats:
   ```bash
   docker stats --no-stream
   ```
2. Query Prometheus for p95 latency and CPU rate by container:
   ```promql
   rate(container_cpu_usage_seconds_total{name=~"payment-service|order-service|inventory-service"}[1m])
   histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))
   ```
3. Inspect container CPU limits:
   ```bash
   docker inspect payment-service --format 'NanoCPUs={{.HostConfig.NanoCPUs}} Cpus={{.HostConfig.CpuQuota}}'
   ```

## Fix
1. Increase CPU limits in `infra/docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1.0'
   ```
   Apply immediately:
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```
2. If traffic is driven by runaway loadgen, temporarily pause or adjust the load generator:
   ```bash
   docker stop loadgen
   ```
3. Scale the service horizontally or increase Uvicorn worker count if multi-core CPUs are available:
   ```bash
   docker compose -f infra/docker-compose.yml up -d --scale payment-service=2
   ```

## Prevention
- Set CPU requests and limits with headroom for traffic spikes.
- Offload CPU-intensive operations (cryptography, large JSON parsing) to background threadpools using `asyncio.to_thread`.
- Establish alerting rules when CPU usage exceeds 85% for more than 3 consecutive minutes.
