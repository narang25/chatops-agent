# payment-service

A sample FastAPI microservice that accepts payments and stores them in Postgres.  
Part of the ChatOps Agent project — this service is used as a target for monitoring, failure injection, and AI-powered diagnosis.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (200 OK, or 500 when `health_fail` fault is on) |
| GET | `/metrics` | Prometheus metrics ([contracts/metrics.md](../../contracts/metrics.md)) |
| POST | `/pay` | Create a payment `{"amount": 42.50}` |
| GET | `/leak` | Allocate ~10 MB of memory that is never freed (OOM testing) |
| POST | `/admin/fault` | Toggle faults `{"health_fail": true, "slow_db": false, "db_error": false}` |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SERVICE_NAME` | Yes | — | Must be `payment-service` |
| `DATABASE_URL` | Yes | — | Postgres connection string |
| `LOG_LEVEL` | No | `INFO` | Python log level |
| `FAULT_HEALTH_FAIL` | No | `false` | Start with health fault on |
| `FAULT_SLOW_DB` | No | `false` | Start with slow DB fault on |
| `FAULT_DB_ERROR` | No | `false` | Start with DB error fault on |

## Run locally (Docker)

```bash
docker build -t payment-service .
docker run -p 8001:8000 \
  -e SERVICE_NAME=payment-service \
  -e DATABASE_URL=postgresql://chatops:change_me@host.docker.internal:5432/chatops \
  payment-service
```

## Run with the full stack

```bash
docker compose -f infra/docker-compose.yml up -d
```

## Log format

Logs are JSON Lines to stdout, matching [contracts/logs.md](../../contracts/logs.md):

```json
{"timestamp": "2026-10-12T10:15:30.123Z", "service": "payment-service", "level": "INFO", "message": "Payment created: id=1 amount=42.5", "extra": {"payment_id": 1, "amount": 42.5}}
```
