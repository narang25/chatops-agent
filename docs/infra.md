# Infrastructure, Microservices, Monitoring & Safe Remediation

This document serves as the comprehensive architectural and operational manual for Person B's infrastructure deliverables across Weeks 1–5: microservices, monitoring, failure injection & chaos testing, telemetry/diagnostic MCP tools, interactive Slack approvals, safe remediation policies, and automated verification/rollback.

---

## 1. Quick Start

### 1.1 Managing the Stack
Docker Desktop must be running. Use the cross-platform CLI (`manage.py`) or Docker Compose:

```bash
# Start all 9 containers (services, databases, monitoring, proxy) in detached mode
python infra/manage.py up

# Check status and health of all containers
python infra/manage.py ps

# Tail logs of a specific service
python infra/manage.py logs payment-service

# Restore all failure toggles, reset memory limits, and clear faults
python infra/manage.py restore

# Stop and tear down the entire stack
python infra/manage.py down
```

### 1.2 Kubernetes Mode (Dual Runtime)
To point MCP tools and remediation to a Kubernetes cluster instead of Docker:
```bash
export RUNTIME=k8s
export KUBECONFIG=~/.kube/config
```
Manifests are pre-validated in `infra/k8s/` (`00-namespace.yaml` through `05-prometheus.yaml`).

---

## 2. Services and Network Topology

| Component | Container Name | Host Port | Internal Port | Health / Status Endpoint | Description |
|---|---|---|---|---|---|
| **Payment Service** | `payment-service` | `8001` | `8000` | `http://localhost:8001/health` | FastAPI payment processor (`/pay`, `/leak`, `/burn`, `/admin/fault`) |
| **Order Service** | `order-service` | `8002` | `8000` | `http://localhost:8002/health` | FastAPI order gateway (`/orders`, `/admin/fault`, Toxiproxy routing) |
| **Inventory Service**| `inventory-service`| `8003` | `8000` | `http://localhost:8003/health` | FastAPI catalog & stock manager (`/stock/{item}`, `/fill`, `/admin/fault`) |
| **PostgreSQL 15** | `postgres` | `5432` | `5432` | `pg_isready` | Database for payment ledger and transactions |
| **Toxiproxy** | `toxiproxy` | `8474` | `8474` | `http://localhost:8474/version` | Network chaos proxy simulating timeouts, latency, and drops |
| **Prometheus** | `prometheus` | `9090` | `9090` | `http://localhost:9090/targets` | Metric aggregation & time-series storage (scrapes every 5s) |
| **cAdvisor** | `cadvisor` | `8085` | `8080` | `http://localhost:8085` | Container cgroup metrics (RSS, limits, CPU throttling) |
| **Grafana** | `grafana` | `3000` | `3000` | `http://localhost:3000` | Pre-provisioned dashboards (User: `admin` / Password: `admin`) |
| **Load Generator** | `loadgen` | — | — | — | Emits background transactions (~1–2 req/s) |

---

## 3. Metrics & Telemetry Specification

All services expose standard Prometheus metrics conforming to `contracts/metrics.md`:

| Metric Name | Type | Labels | Description |
|---|---|---|---|
| `http_requests_total` | Counter | `service`, `endpoint`, `status` | Total HTTP requests handled |
| `http_request_duration_seconds` | Histogram | `service`, `endpoint` | Request latency distribution |
| `app_errors_total` | Counter | `service` | Application-level error events logged |
| `app_memory_bytes` | Gauge | `service` | Process RSS memory consumption in bytes |
| `app_up` | Gauge | `service` | Operational health (`1` = healthy, `0` = unhealthy) |

Container metrics are collected directly via cAdvisor:
- `container_memory_usage_bytes{name="<service>"}`
- `container_spec_memory_limit_bytes{name="<service>"}`
- `container_cpu_usage_seconds_total{name="<service>"}`

---

## 4. Complete 10-Scenario Failure Suite

All 10 scenarios are executable via `infra/failures/run_scenario.py` and have corresponding ground truth schemas under `infra/failures/ground_truth/`:

```bash
# List available scenarios
python infra/failures/run_scenario.py list

# Run a scenario
python infra/failures/run_scenario.py run <scenario_id>

# Validate ground truth schemas
python infra/failures/run_scenario.py validate

# Restore clean baseline
python infra/failures/run_scenario.py restore
```

| Scenario ID | Failure Type | Target Service | Script | Fault Mechanism | Key Diagnostic Signals |
|---|---|---|---|---|---|
| `oom-payment-001` | `out_of_memory` | `payment-service` | `oom.py` | Sets memory limit to 64MB, triggers `/leak` | Exit code 137, `oom_killed=True`, restart spikes, memory >= limit |
| `badenv-order-001` | `bad_config` | `order-service` | `bad_env.py` | Starts container missing `PAYMENT_SERVICE_URL` | Exit code 1, fast container crash loop, fatal startup exception log |
| `healthfail-inventory-001` | `health_check_failure` | `inventory-service` | `health_fail.py` | Sets `health_fail=true` via `/admin/fault` | `/health` returns 500, state `unhealthy`, `app_up` drops to 0 |
| `dbtimeout-payment-001` | `db_timeout` | `payment-service` | `db_timeout.py` | Sets `slow_db=true` via `/admin/fault` | Requests delay >=3s, p95 latency spikes, connection timeouts |
| `depfail-order-001` | `dependency_failure` | `order-service` | `dependency_failure.py` | Shuts down `payment-service` container | HTTP 502 Bad Gateway on `/orders`, connection refused logs |
| `cpusat-payment-001` | `cpu_saturation` | `payment-service` | `cpu_saturation.py` | CPU limited to 0.5 cores, triggers `/burn` | cAdvisor throttling spikes, p95 request duration elevation |
| `diskfull-inventory-001` | `disk_full` | `inventory-service` | `disk_full.py` | Calls `/fill` filling ephemeral disk partition | HTTP 507 Insufficient Storage, disk full log events |
| `netdrop-order-001` | `network_timeout` | `order-service` | `network_timeout.py` | Injects Toxiproxy timeout/packet drop toxic | Network timeouts calling downstream dependency |
| `baddeploy-order-001` | `bad_deploy` | `order-service` | `bad_deploy.py` | Simulates deployment of buggy image v2 | Sudden error rate surge immediately following deployment event |
| `crashloop-inventory-001` | `crash_loop` | `inventory-service` | `crash_loop.py` | Container repeatedly crashes on startup | State `crash_loop_backoff`, restart count monotonically increasing |

### 4.1 Chaos Suite & Incident Recorder
- **Incident Recorder** (`infra/failures/recorder.py`): Captures telemetry snapshots into `data/incident_logs/<scenario_id>/<run_id>/`:
  - `logs.jsonl`: Service JSON logs
  - `metrics.json`: Time-series Prometheus metrics
  - `events.json`: Container lifecycle events
  - `pod_status.json`: Container runtime status
  - `ground_truth.json`: Scenario expected root cause & remediation
- **Chaos Runner** (`infra/failures/chaos_suite.py`):
  ```bash
  python infra/failures/chaos_suite.py --repeat 2 --seed 42 --jitter 5
  ```
  Appends run manifests to `data/incident_logs/chaos_manifest.jsonl`.

---

## 5. Telemetry & Diagnostic MCP Tools

Person B provides 7 production-grade Model Context Protocol (MCP) tools across two servers conforming to `contracts/mcp_tools.md`:

### 5.1 Prometheus MCP Server (`mcp_servers/prometheus/server.py`)
1. **`get_metrics(service, metric, minutes=10, step="15s")`**:
   - Queries time-series values from Prometheus for a target service.
   - Returns: `{"service": ..., "metric": ..., "query": ..., "values": [[ts, val], ...]}`.
2. **`get_anomalies(service, minutes=10, baseline_minutes=60)`**:
   - Compares the active incident window against a pre-incident baseline window across error rates, p95 latency, restart counts, and memory growth.
   - Integrates **Drain3** log clustering to extract new error templates that appeared during the incident window.
   - Returns: `{"service": ..., "anomalies": [...], "new_log_patterns": [...]}`.

### 5.2 Kubernetes / Docker MCP Server (`mcp_servers/kubernetes/server.py`)
3. **`get_pod_status(service)`**:
   - Returns container/pod lifecycle state (`running`, `healthy`, `unhealthy`, `oom_killed`, `crash_loop_backoff`), restart count, and memory limit in MB.
4. **`get_events(service, minutes=10)`**:
   - Returns recent Docker/K8s events (e.g. `kill`, `die`, `restart`, `OOMKilled`).
5. **`get_logs(service, minutes=10, level="ERROR", limit=100)`**:
   - Extracts structured JSON log entries filtered by time and log severity.
6. **`list_services()`**:
   - Lists all monitored services with operational states.
7. **`what_changed(service, minutes=60)`**:
   - Correlates multi-source deployment and operational changes:
     - Local deployment events (`data/deploy_events.jsonl`)
     - Container lifecycle events (`start`, `restart`, `update`, `kill`)
     - GitHub REST API commits (via `GITHUB_READ_TOKEN` / `GITHUB_REPOSITORY`)
   - Returns: `{"service": ..., "changes": [...]}`.

---

## 6. Remediation MCP Server & Safety Model

### 6.1 Core Principle: Human-in-the-Loop
> [!IMPORTANT]
> The AI Agent is strictly **read-and-propose only**. It is NEVER granted direct execution access to `apply_remediation`. The agent calls `propose_remediation`. Execution requires human approval in Slack, which exchanges a cryptographically signed, single-use token.

```
+----------------+          +-------------------------+          +-------------------------+
|   AI Agent     |  ----->  |   propose_remediation   |  ----->  | Generates Proposal &    |
| (Root Cause)   |          |      (Dry Run)          |          | Single-Use HMAC Token   |
+----------------+          +-------------------------+          +-------------------------+
                                                                              |
                                                                              v
+----------------+          +-------------------------+          +-------------------------+
|   Audit Log    |  <-----  |    apply_remediation    |  <-----  | Interactive Slack Card: |
| (.jsonl file)  |          | (Token + Approver Check)|          | [Approve] / [Reject]    |
+----------------+          +-------------------------+          +-------------------------+
         |
         v
+-------------------------+          +-------------------------+
| Background Verification |  ----->  | Degraded? Auto-Rollback |
| Engine (3 min window)   |          | Improved? Post Confirmed|
+-------------------------+          +-------------------------+
```

### 6.2 Policy Enforcement (`infra/remediation_policy.yaml`)
- **Action Whitelist**: `restart_service`, `set_memory_limit`, `rollback_deploy`, `scale_service`.
- **Target Whitelist**: `payment-service`, `order-service`, `inventory-service`.
- **Parameter Bounds**: Memory limits strictly enforced between 64MB and 512MB.
- **Risk Classification**: Actions classified as `low`, `medium`, or `high` risk.

### 6.3 Slack Interactive Approvals (`interfaces/slack/app.py`)
- Renders rich Slack Block Kit cards with proposal details, risk rating, and `[✅ Approve & Apply]` / `[❌ Reject]` buttons.
- Verifies approver identity against `APPROVER_SLACK_IDS` from `.env.infra`.
- Validates single-use token; rejects expired (>5 min) or reused tokens.

### 6.4 Verification Engine & Automatic Rollback
- Upon application, the server snapshots baseline container state (memory limit, restart count, health).
- Spawns an asynchronous verification watcher.
- If health degrades (new OOM, crash loop, unhealthy status, or restart spike), the engine automatically issues a rollback to the snapshot baseline, updates `data/audit_log.jsonl` with `auto_rollback_completed`, and posts an alert to Slack.

---

## 7. 10-Minute Live Demo & Rehearsal Script

Follow this step-by-step sequence for project presentations:

### Step 1: Baseline Check
```bash
python infra/manage.py up
python infra/manage.py ps
```
Ensure all 3 sample microservices are running healthy.

### Step 2: Failure Injection
```bash
python infra/failures/run_scenario.py run oom-payment-001
```
Observe payment service memory leak and OOM crash.

### Step 3: Run Diagnostic MCP Tools
In Python or test harness:
```python
from mcp_servers.kubernetes.server import get_pod_status, what_changed
from mcp_servers.prometheus.server import get_anomalies

print(get_pod_status("payment-service"))
# Shows state: "oom_killed", restarts > 0

print(get_anomalies("payment-service"))
# Shows memory growth anomaly and exit 137 log patterns

print(what_changed("payment-service"))
# Correlates recent restart/kill lifecycle events
```

### Step 4: Propose Remediation (Agent Action)
```python
from mcp_servers.remediation.server import propose_remediation

proposal = propose_remediation(
    service="payment-service",
    action="set_memory_limit",
    params={"memory_mb": 256},
    reason="Payment service experienced OOM at 64MB limit under leak scenario."
)
print(proposal)
# Returns proposal_id, risk: "medium", and approval_token
```

### Step 5: Slack Human Approval & Execution
In Slack (or via test harness simulating approval):
```python
from mcp_servers.remediation.server import apply_remediation

result = apply_remediation(
    proposal_id=proposal["proposal_id"],
    token=proposal["approval_token"],
    approver="U12345678"
)
print(result)
# Returns status: "applied", spawns post-fix verification
```

### Step 6: Verify and Rollback Demonstration
Inspect `data/audit_log.jsonl` to observe the immutable audit trail of proposed, applied, and verified states.

### Step 7: Restore
```bash
python infra/manage.py restore
```
Resets all limits and faults cleanly back to baseline.
