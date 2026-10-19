---
title: "Missing Environment Variable: Order Service Startup Failure"
failure_type: bad_config
service: order-service
severity: high
---

## Symptoms
- Container immediately crashes upon startup with exit code `1`.
- Container enters `exited` or `CrashLoopBackOff` status.
- Container stdout logs show a CRITICAL startup error:
  `{"timestamp": "2026-10-13T11:46:57.855Z", "service": "order-service", "level": "CRITICAL", "message": "PAYMENT_SERVICE_URL environment variable is required but not set"}`
- Prometheus reports `app_up{service="order-service"} == 0` or metrics endpoint unreachable.

## Likely cause
- Required environment variable `PAYMENT_SERVICE_URL` is missing from the environment configuration or Docker Compose file.
- Typo in environment variable name during deployment (e.g. `PAYMENT_URL` instead of `PAYMENT_SERVICE_URL`).
- `.env` file not mounted or passed to container runtime.

## How to confirm
1. Check container exit code and error logs:
   ```bash
   docker inspect order-service --format 'State={{.State.Status}} ExitCode={{.State.ExitCode}}'
   docker logs --tail 20 order-service
   ```
2. Verify existing environment variables inside container or inspect compose definition:
   ```bash
   docker inspect order-service --format '{{json .Config.Env}}'
   ```
3. Look for missing `PAYMENT_SERVICE_URL` or `DATABASE_URL`.

## Fix
1. Add the missing variable to `infra/docker-compose.yml` under `order-service.environment`:
   ```yaml
   environment:
     - PAYMENT_SERVICE_URL=http://payment-service:8001
     - INVENTORY_SERVICE_URL=http://inventory-service:8003
     - DATABASE_URL=postgresql://chatops:chatops123@postgres:5432/chatops
   ```
2. Recreate and restart `order-service`:
   ```bash
   docker compose -f infra/docker-compose.yml up -d order-service
   ```
3. Confirm container is healthy and handling traffic:
   ```bash
   curl -f http://localhost:8002/health
   ```

## Prevention
- Implement fail-fast configuration validation at build time or deployment pipeline checks (`docker compose config`).
- Provide `.env.example` templates with all mandatory keys clearly listed and required checks in CI.
- Use Kubernetes ConfigMaps / Secrets with strict schema validation.
