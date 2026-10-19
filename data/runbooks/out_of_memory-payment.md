---
title: "OOMKilled: Payment Service Memory Limit Exceeded"
failure_type: out_of_memory
service: payment-service
severity: high
---

## Symptoms
- Container restarts suddenly or enters a crash-restart cycle.
- Docker inspect reveals `OOMKilled: true` or exit code `137` (SIGKILL).
- Application logs show rapid memory allocation before termination:
  `{"timestamp": "2026-10-13T11:47:45.668Z", "service": "payment-service", "level": "WARNING", "message": "Memory leak: allocated 10 MB, total leaked: 20 MB"}`
- Prometheus metric `app_memory_bytes{service="payment-service"}` increases monotonically until process dies.

## Likely cause
- The container memory limit (e.g. 64MB) is insufficient for transaction load.
- Unbounded in-memory accumulation triggered by memory leak endpoints (`/leak`) or unreleased payload caches in payment processing.
- Python garbage collection delays under heavy concurrent request spikes.

## How to confirm
1. Inspect container exit state using Docker:
   ```bash
   docker inspect payment-service --format 'OOMKilled={{.State.OOMKilled}} ExitCode={{.State.ExitCode}} Restarts={{.RestartCount}}'
   ```
2. Query Prometheus for resident memory usage vs container limits:
   ```promql
   container_memory_usage_bytes{name="payment-service"}
   app_memory_bytes{service="payment-service"}
   ```
3. Check application logs immediately preceding restart:
   ```bash
   docker logs --tail 50 payment-service
   ```

## Fix
1. Immediate mitigation: restart container to flush transient leaked memory:
   ```bash
   docker restart payment-service
   ```
2. Increase the container memory limit in `infra/docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 256M
   ```
   Apply changes with:
   ```bash
   docker compose -f infra/docker-compose.yml up -d payment-service
   ```
3. Reset any active simulated leak via fault recovery script:
   ```bash
   python infra/failures/restore.py
   ```

## Prevention
- Configure memory alerts when `container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.80`.
- Profile heap allocations using `tracemalloc` to prevent memory retention across requests.
- Enforce strict request payload limits (e.g. 1MB) on payment ingest endpoints.
