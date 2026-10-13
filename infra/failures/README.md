# Failure Injection Scenarios & Incident Log Capture

This folder contains failure injection scripts that create realistic incidents, capture symptoms into JSON logs, and generate ground truth metadata for the ChatOps AI agent benchmark.

## Scenarios

| Script | Failure Type | Target Service | Injected Fault | Expected Symptoms |
|---|---|---|---|---|
| `oom.py` | `out_of_memory` | `payment-service` | Limits memory to 64MB and triggers `/leak` | Container killed (exit 137), `OOMKilled=true`, restart count increases |
| `bad_env.py` | `bad_config` | `order-service` | Starts container missing `PAYMENT_SERVICE_URL` | Critical startup JSON log, exit code 1, container crash loop |
| `health_fail.py` | `health_check_failure` | `inventory-service` | Toggles `health_fail` flag via `/admin/fault` | `/health` returns 500, Docker status `unhealthy`, `app_up` drops to 0 |

## How to Run

Before running any scenario, ensure the compose stack is running:
```bash
docker compose -f infra/docker-compose.yml up -d
```

### 1. Run Out-Of-Memory Scenario
```bash
python infra/failures/oom.py
```
Output files:
- `data/incident_logs/oom-payment-001.jsonl`
- `data/incident_logs/oom-payment-001.meta.json`

### 2. Run Misconfiguration Scenario
```bash
python infra/failures/bad_env.py
```
Output files:
- `data/incident_logs/badenv-order-001.jsonl`
- `data/incident_logs/badenv-order-001.meta.json`

### 3. Run Health Check Failure Scenario
```bash
python infra/failures/health_fail.py
```
Output files:
- `data/incident_logs/healthfail-inventory-001.jsonl`
- `data/incident_logs/healthfail-inventory-001.meta.json`

## How to Restore

To restore all services back to normal healthy operations:
```bash
python infra/failures/restore.py
# Or on bash:
bash infra/failures/restore.sh
```
