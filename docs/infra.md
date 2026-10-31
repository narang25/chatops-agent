# Infrastructure, Services, and Monitoring Documentation

This document covers the sample microservices, monitoring stack, failure injection procedures, and Prometheus diagnostic queries for Person B's deliverables (Weeks 1 & 2).

---

## 1. Quick Start

### 1.1 Managing the Stack
Ensure Docker Desktop is running. You can manage the entire environment using either the cross-platform Python CLI or the Makefile:

**Cross-platform CLI (Windows / macOS / Linux):**
```bash
python infra/manage.py up        # Start all 8 containers in background
python infra/manage.py ps        # Check status of all containers
python infra/manage.py logs [svc]# Tail logs (e.g. python infra/manage.py logs payment-service)
python infra/manage.py restore   # Reset all fault toggles and memory limits
python infra/manage.py down      # Stop and tear down stack
```

**Or using make (Linux / macOS):**
```bash
make -C infra up
make -C infra ps
make -C infra restore
make -C infra down
```

**Or raw docker compose:**
```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml down
```

This launches 8 containers:
- 3 FastAPI sample microservices (`payment-service`, `order-service`, `inventory-service`)
- PostgreSQL 15 (`postgres`)
- Prometheus (`prometheus`)
- Grafana (`grafana`)
- cAdvisor (`cadvisor`)
- Background load generator (`loadgen`)

---

## 2. Services and Ports

| Component | Container Name | Host Port | Internal Port | Health URL | Description |
|---|---|---|---|---|---|
| **Payment Service** | `payment-service` | `8001` | `8000` | `http://localhost:8001/health` | Payment processing backed by Postgres (`/pay`, `/leak`, `/burn`) |
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

Container-level metrics (e.g. `container_memory_usage_bytes`, `container_spec_memory_limit_bytes`, `container_cpu_usage_seconds_total`) are scraped directly from cAdvisor.

---

## 4. Failure Scenarios and Reproduction

Failure scripts reside in `infra/failures/`. Each script injects a failure, captures valid JSON logs into `data/incident_logs/<scenario_id>.jsonl`, and generates ground truth in `data/incident_logs/<scenario_id>.meta.json`.

All 6 scenarios can be executed via the unified runner:
```bash
python infra/failures/run_scenario.py list
python infra/failures/run_scenario.py run <scenario_id>
python infra/failures/run_scenario.py restore
```

### 4.1 Scenario Reference

| Scenario ID | Failure Type | Target Service | Script | Injected Fault | Expected Key Signals |
|---|---|---|---|---|---|
| `oom-payment-001` | `out_of_memory` | `payment-service` | `oom.py` | Memory limited to 64MB, calls `/leak` | Container killed (exit 137), restart count increases, memory near limit |
| `badenv-order-001` | `bad_config` | `order-service` | `bad_env.py` | Starts container missing `PAYMENT_SERVICE_URL` | Critical startup JSON log, exit code 1, container crash loop |
| `healthfail-inventory-001` | `health_check_failure` | `inventory-service` | `health_fail.py` | Sets `health_fail=true` via `/admin/fault` | `/health` returns 500, Docker status `unhealthy`, `app_up` drops to 0 |
| `dbtimeout-payment-001` | `db_timeout` | `payment-service` | `db_timeout.py` | Sets `slow_db=true` via `/admin/fault` | Requests delayed >=3s, latency spikes, DB timeouts |
| `depfail-order-001` | `dependency_failure` | `order-service` | `dependency_failure.py` | Stops `payment-service` container | `order-service` returns HTTP 502, connection refused logs |
| `cpusat-payment-001` | `cpu_saturation` | `payment-service` | `cpu_saturation.py` | High compute loops via `/burn` (limit 0.5 CPU) | cAdvisor CPU throttled, elevated p95 latency |

### 4.2 Restoring Baseline State
```bash
python infra/failures/restore.py
# Or on Unix / Git Bash:
bash infra/failures/restore.sh
# Or using manage.py:
python infra/manage.py restore
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

---

## 7. Connecting Person A's Agent to Live MCP Tools

Person A's `agent/api.py` uses stubs by default (`agent/stub_tools.py`). To switch to real MCP tools provided by Person B:

```python
# In agent/api.py (or via an environment toggle USE_REAL_MCP=true):
from mcp_servers.prometheus.server import get_metrics as real_get_metrics
from mcp_servers.kubernetes.server import (
    get_pod_status as real_get_pod_status,
    get_events as real_get_events,
    get_logs as real_get_logs,
    list_services as real_list_services,
)
```

The function signatures and return dictionaries match `agent/stub_tools.py` and `contracts/mcp_tools.md` exactly, allowing transparent plug-and-play.
