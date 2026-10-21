# Failure Injection Scenarios & Incident Log Capture

This folder contains failure injection scripts that create realistic incidents, capture symptoms into JSON logs, and generate ground truth metadata for the ChatOps AI agent benchmark.

## Scenarios Suite (All 6 Failure Types)

| Scenario ID | Failure Type | Target Service | Script | Injected Fault | Expected Key Signals |
|---|---|---|---|---|---|
| `oom-payment-001` | `out_of_memory` | `payment-service` | `oom.py` | Memory limited to 64MB, calls `/leak` | Container killed (exit 137), restart count increases, memory near limit |
| `badenv-order-001` | `bad_config` | `order-service` | `bad_env.py` | Starts container missing `PAYMENT_SERVICE_URL` | Critical startup JSON log, exit code 1, container crash loop |
| `healthfail-inventory-001` | `health_check_failure` | `inventory-service` | `health_fail.py` | Sets `health_fail=true` via `/admin/fault` | `/health` returns 500, Docker status `unhealthy`, `app_up` drops to 0 |
| `dbtimeout-payment-001` | `db_timeout` | `payment-service` | `db_timeout.py` | Sets `slow_db=true` via `/admin/fault` | Requests delayed >=3s, latency spikes, DB timeouts |
| `depfail-order-001` | `dependency_failure` | `order-service` | `dependency_failure.py` | Stops `payment-service` container | `order-service` returns HTTP 502, connection refused logs |
| `cpusat-payment-001` | `cpu_saturation` | `payment-service` | `cpu_saturation.py` | High compute loops via `/burn` (limit 0.5 CPU) | cAdvisor CPU throttled, elevated p95 latency |

## Unified Runner (`run_scenario.py`)

Person A's benchmark and local tests execute failures via `run_scenario.py`:

```bash
# 1. List all available scenarios
python infra/failures/run_scenario.py list

# 2. Inject a scenario (leaves environment broken for agent diagnosis)
python infra/failures/run_scenario.py run oom-payment-001

# 3. Restore stack to baseline healthy state
python infra/failures/run_scenario.py restore
```

## How to Restore

To restore all services back to normal healthy operations:
```bash
python infra/failures/restore.py
# Or on Unix / Git Bash:
bash infra/failures/restore.sh
# Or using the unified runner:
python infra/failures/run_scenario.py restore
```
