# Infrastructure, Services, and Monitoring Documentation

This document covers the sample microservices, monitoring stack, failure injection procedures, and Prometheus diagnostic queries for Person B's deliverables (Week 1).

---

## 1. Quick Start

### 1.1 Starting the Stack
Ensure Docker Desktop is running, then run:
```bash
docker compose -f infra/docker-compose.yml up -d
```
This launches 8 containers:
- 3 FastAPI sample microservices (`payment-service`, `order-service`, `inventory-service`)
- PostgreSQL 15 (`postgres`)
- Prometheus (`prometheus`)
- Grafana (`grafana`)
- cAdvisor (`cadvisor`)
- Background load generator (`loadgen`)

### 1.2 Stopping the Stack
```bash
docker compose -f infra/docker-compose.yml down
```

---

## 2. Services and Ports

| Component | Container Name | Host Port | Internal Port | Health URL | Description |
|---|---|---|---|---|---|
| **Payment Service** | `payment-service` | `8001` | `8000` | `http://localhost:8001/health` | Payment processing backed by Postgres (`/pay`, `/leak`) |
| **Order Service** | `order-service` | `8002` | `8000` | `http://localhost:8002/health` | Order placement, calls `payment-service` (`/orders`) |
| **Inventory Service** | `inventory-service` | `8003` | `8000` | `http://localhost:8003/health` | Stock lookups and updates (`/stock/{item}`) |
| **PostgreSQL** | `postgres` | `5432` | `5432` | *(pg_isready check)* | Relational database (`chatops` database) |
| **Prometheus** | `prometheus` | `9090` | `9090` | `http://localhost:9090/targets` | Scrapes `/metrics` every 5 seconds |
| **Grafana** | `grafana` | `3000` | `3000` | `http://localhost:3000` | Pre-provisioned dashboards (user: `admin` / pass: `admin`) |
| **cAdvisor** | `cadvisor` | `8085` | `8080` | `http://localhost:8085` | Container CPU, RSS, memory limits metrics |
| **Load Generator** | `loadgen` | — | — | — | Emits steady background traffic (~1-2 req/s) |

---

## 3. Metrics Exposed by Services

Each service exposes standard Prometheus metrics at `GET /metrics` conforming to `contracts/metrics.md`:

| Metric Name | Type | Description |
|---|---|---|
| `http_requests_total{service, endpoint, status}` | Counter | Total HTTP requests handled |
| `http_request_duration_seconds{service, endpoint}` | Histogram | HTTP request latency distribution |
| `app_errors_total{service}` | Counter | Application-level error events logged |
| `app_memory_bytes{service}` | Gauge | Process RSS memory measured in bytes |
| `app_up{service}` | Gauge | Service operational health (`1` = healthy, `0` = unhealthy) |

Container-level metrics (e.g. `container_memory_usage_bytes`, `container_spec_memory_limit_bytes`) are scraped directly from cAdvisor.

---

## 4. Failure Scenarios and Reproduction

Failure scripts reside in `infra/failures/`. Each script injects a failure, captures valid JSON logs into `data/incident_logs/<scenario_id>.jsonl`, and generates ground truth in `data/incident_logs/<scenario_id>.meta.json`.

### Scenario 1: Out Of Memory (`oom.py`)
- **Target**: `payment-service`
- **Mechanism**: Constrains container memory limit to 64MB via `docker update`, then triggers `/leak` until the container is OOM-killed and restarts.
- **Run command**:
  ```bash
  python infra/failures/oom.py
  ```
- **Generated artifacts**:
  - `data/incident_logs/oom-payment-001.jsonl`
  - `data/incident_logs/oom-payment-001.meta.json`

### Scenario 2: Misconfiguration (`bad_env.py`)
- **Target**: `order-service`
- **Mechanism**: Starts an instance missing the required `PAYMENT_SERVICE_URL` variable. The app logs a `CRITICAL` error on startup and exits with code 1.
- **Run command**:
  ```bash
  python infra/failures/bad_env.py
  ```
- **Generated artifacts**:
  - `data/incident_logs/badenv-order-001.jsonl`
  - `data/incident_logs/badenv-order-001.meta.json`

### Scenario 3: Health Check Failure (`health_fail.py`)
- **Target**: `inventory-service`
- **Mechanism**: Toggles runtime fault `health_fail=true` via `POST /admin/fault`. The service returns HTTP 500 on `/health` and drops `app_up` to 0.
- **Run command**:
  ```bash
  python infra/failures/health_fail.py
  ```
- **Generated artifacts**:
  - `data/incident_logs/healthfail-inventory-001.jsonl`
  - `data/incident_logs/healthfail-inventory-001.meta.json`

### 4.4 How to Restore Everything
To bring all services back to a normal healthy state:
```bash
python infra/failures/restore.py
# Or on Unix / Git Bash:
bash infra/failures/restore.sh
```

---

## 5. Useful Prometheus Queries for AI Diagnosis

These queries can be used in Prometheus (`http://localhost:9090`) or via MCP tools in Week 2:

- **Check if a service is healthy (up/down)**:
  ```promql
  app_up{service="payment-service"}
  ```
- **Request rate over the last 1 minute**:
  ```promql
  sum by (service, endpoint) (rate(http_requests_total[1m]))
  ```
- **Error rate (non-200 or app errors)**:
  ```promql
  sum by (service) (rate(app_errors_total[1m]))
  ```
- **Process RSS Memory**:
  ```promql
  app_memory_bytes{service="payment-service"}
  ```
- **Container memory relative to its memory limit (cAdvisor)**:
  ```promql
  container_memory_usage_bytes{name="payment-service"} / container_spec_memory_limit_bytes{name="payment-service"} * 100
  ```

---

## 6. Incident Files Summary

Captured incidents are committed under `data/incident_logs/`:
- `*.jsonl`: Pure JSON-line logs emitted by the affected service during the incident window.
- `*.meta.json`: Ground truth metadata documenting `scenario_id`, `service`, `failure_type`, `root_cause`, `expected_fix`, and observed `signals`. These files serve as test inputs for Person A's runbooks and Week 4 benchmark validation.
