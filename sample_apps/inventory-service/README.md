# inventory-service

A sample FastAPI microservice that manages item stock and inventory in Postgres.  
Part of the ChatOps Agent project — this service is used as a target for monitoring, failure injection, and AI-powered diagnosis.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check (200 OK, or 500 when `health_fail` fault is on) |
| GET | `/metrics` | Prometheus metrics ([contracts/metrics.md](../../contracts/metrics.md)) |
| GET | `/stock/{item}` | Look up item stock quantity `{"item": "widget", "quantity": 100}` |
| POST | `/stock/{item}` | Update stock quantity `{"quantity": 120}` |
| POST | `/admin/fault` | Toggle faults `{"health_fail": true, "slow_db": false, "db_error": false}` |

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SERVICE_NAME` | Yes | — | Must be `inventory-service` |
| `DATABASE_URL` | Yes | — | Postgres connection string |
| `LOG_LEVEL` | No | `INFO` | Python log level |
| `FAULT_HEALTH_FAIL` | No | `false` | Start with health fault on |
| `FAULT_SLOW_DB` | No | `false` | Start with slow DB fault on |
| `FAULT_DB_ERROR` | No | `false` | Start with DB error fault on |

## Run locally (Docker)

```bash
docker build -t inventory-service .
docker run -p 8003:8000 \
  -e SERVICE_NAME=inventory-service \
  -e DATABASE_URL=postgresql://chatops:change_me@host.docker.internal:5432/chatops \
  inventory-service
```

## Run with the full stack

```bash
docker compose -f infra/docker-compose.yml up -d
```

## Log format

Logs are JSON Lines to stdout, matching [contracts/logs.md](../../contracts/logs.md):

```json
{"timestamp": "2026-10-12T10:15:30.123Z", "service": "inventory-service", "level": "INFO", "message": "Stock retrieved: item=widget quantity=100", "extra": {"item": "widget", "quantity": 100}}
```
