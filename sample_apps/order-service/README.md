# order-service

A sample FastAPI microservice that processes customer orders, interacts with `payment-service` over HTTP, and persists order records in PostgreSQL.  
Part of the ChatOps Agent project — this service is used as a target for monitoring, dependency tracking, failure injection, and AI-powered diagnosis.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (200 OK, or 500 when `health_fail` fault is on) |
| GET | `/metrics` | Prometheus metrics ([contracts/metrics.md](../../contracts/metrics.md)) |
| POST | `/orders` | Create an order `{"item": "widget", "quantity": 2, "amount": 42.50}` (calls payment-service `/pay`) |
| GET | `/orders/{order_id}` | Fetch order record by ID from Postgres |
| POST | `/admin/fault` | Toggle faults `{"health_fail": true, "slow_db": false, "db_error": false}` |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SERVICE_NAME` | Yes | — | Must be `order-service` |
| `DATABASE_URL` | Yes | — | Postgres connection string |
| `PAYMENT_SERVICE_URL` | Yes | — | Base URL of payment-service (e.g. `http://payment-service:8000`) |
| `LOG_LEVEL` | No | `INFO` | Python log level |
| `FAULT_HEALTH_FAIL` | No | `false` | Start with health fault on |
| `FAULT_SLOW_DB` | No | `false` | Start with slow DB fault on (3s delay) |
| `FAULT_DB_ERROR` | No | `false` | Start with DB error fault on |

If any required variable (`SERVICE_NAME`, `DATABASE_URL`, or `PAYMENT_SERVICE_URL`) is missing on startup, the application logs a `CRITICAL` JSON message and exits with status code `1`.

## Run locally (Docker)

```bash
docker build -t order-service .
docker run -p 8002:8000 \
  -e SERVICE_NAME=order-service \
  -e DATABASE_URL=postgresql://chatops:change_me@host.docker.internal:5432/chatops \
  -e PAYMENT_SERVICE_URL=http://host.docker.internal:8001 \
  order-service
```

## Run with the full stack

```bash
docker compose -f infra/docker-compose.yml up -d
```

## Log format

Logs are JSON Lines written to stdout, matching [contracts/logs.md](../../contracts/logs.md):

```json
{"timestamp": "2026-10-12T10:15:30.123Z", "service": "order-service", "level": "INFO", "message": "Order created: id=1 item=widget quantity=2 payment_id=10", "extra": {"order_id": 1, "item": "widget", "quantity": 2, "payment_id": 10, "amount": 42.5}}
```
