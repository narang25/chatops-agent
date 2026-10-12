# ChatOps Project: Person B Brief (Infra, Tools, Failures, Interfaces)

> How to use this file: put it in the repo root (or paste it into your IDE agent as the project brief) and tell the agent:
> "Read PERSON_B_BRIEF.md fully. We are working on Week 1 only. Follow the folder ownership and git rules strictly. Build step by step and ask me before doing anything outside Week 1."

---

## 1. What we are building

### 1.1 The one-line version
An open-source, AI-powered **SRE / ChatOps agent**. When a deployment or service fails, an engineer asks "why did payment-service fail?" in a CLI (later Slack). The agent searches runbooks and past incidents, pulls **live metrics and container/pod status** through **MCP tools**, reasons about it with an LLM, and replies with a **cited diagnosis and a suggested fix**.

### 1.2 The problem it solves
When something breaks at 2 AM, an engineer has to jump between logs, Grafana, kubectl and old docs, and often depends on a senior teammate who "just knows". Our agent does that investigation in one place and shows its evidence.

### 1.3 Why this is not "just a chatbot over data"
Our professor asked what is different. Our answer:
1. **Tool-using agent via MCP**, not a document chatbot. The agent calls live tools (metrics, pod status, events).
2. **Static knowledge + live signals together**: runbooks and past incidents (RAG) combined with current Prometheus data.
3. **Explainable**: every answer cites its sources (runbook, log line, metric).
4. **Later weeks**: multi-agent diagnosis, safe approval-gated remediation with verification and rollback, and a **chaos-based benchmark** that scores the agent automatically.

### 1.4 Architecture (simple view)

```
 Engineer (CLI now, Slack later)
            |
            v
     Agent (Person A)  <-- LLM (AWS Bedrock / Ollama fallback)
        |        |        \
        |        |         \--> search_runbooks  (MCP server, Person A)  --> Chroma vector DB
        |        |
        |        +------------> get_metrics      (MCP server, Person B)  --> Prometheus
        +---------------------> get_pod_status   (MCP server, Person B)  --> Docker / Kubernetes
                                get_events       (MCP server, Person B)

 Sample microservices (Person B) --> logs + /metrics --> Prometheus --> Grafana
 Failure injection scripts (Person B) deliberately break the services to create realistic incidents
```

### 1.5 Who owns what
- **Person A**: the "brain": LLM setup, RAG over runbooks, the agent, the CLI, the `search_runbooks` MCP server.
- **Person B (you)**: the "body and tools": sample microservices, monitoring stack, failure injection, incident logs, the MCP servers for metrics and pod status, later the Slack bot, Minikube, CI/CD, chaos testing and remediation.

You build the world the agent investigates and the tools it uses to look at that world.

---

## 2. Rules for the IDE agent (read carefully)

### 2.1 Folder ownership (the main way we avoid merge conflicts)
Only edit files in YOUR folders. Never edit Person A's folders.

```
repo/
├── agent/                 A only
├── rag/                   A only
├── mcp_servers/
│   ├── runbooks/          A only
│   ├── prometheus/        B (you)
│   └── kubernetes/        B (you)
├── interfaces/
│   ├── cli/               A only
│   └── slack/             B (you), starts Week 3
├── sample_apps/           B (you)
├── infra/                 B (you)  (docker-compose, prometheus.yml, grafana, k8s manifests, failure scripts)
├── data/
│   ├── runbooks/          A only
│   └── incident_logs/     B (you)
├── contracts/             SHARED, do not edit without telling the team
└── docs/
    ├── agent.md           A only
    └── infra.md           B (you)
```

### 2.2 Files that must not be shared
- Your Python dependencies go in `requirements-infra.txt` (never `requirements.txt`).
- Your env example is `.env.infra.example` (never `.env.example`). Real `.env` files are never committed.
- `docker-compose.yml` lives in `infra/` and is yours only.
- Do not create a shared `utils.py` at the repo root. Keep helpers inside your own folders.
- Do not edit `README.md` (Person A owns it). Write your notes in `docs/infra.md`.

### 2.3 Git rules
- Never commit to `main`. Branch names: `feat/b-<short-name>`, e.g. `feat/b-sample-apps`, `feat/b-prometheus-mcp`.
- Start every work session with `git pull --rebase origin main`.
- Commit small and often, push at least once a day, open a PR for every merge and have Person A review it. Merge the same day if possible.
- `.gitignore` must cover: `.env`, `__pycache__/`, `.venv/`, `chroma_db/`, `*.log` (but NOT `data/incident_logs/*.jsonl`, we want those committed).
- Changes in `contracts/` need their own PR, approved by both people.
- Never put API keys, AWS credentials or tokens in the repo.

### 2.4 Working style for the agent
- Work one task at a time. After each task, show how to run and verify it, then wait.
- Prefer simple, readable code with comments. This is a student project that we must be able to explain in a viva.
- Every folder you create gets a short README explaining what it does and how to run it.

---

## 3. Contracts (proposed defaults, finalise with Person A on Day 1)

These make sure your work fits her code without you two waiting on each other.

### 3.1 Log format: JSON Lines, one JSON object per line
Every sample service must write logs to stdout in exactly this shape:

```json
{"timestamp": "2026-10-12T10:15:30.123Z", "service": "payment-service", "level": "ERROR", "message": "Database connection timed out after 5s", "extra": {"request_id": "abc123"}}
```

- `timestamp`: ISO 8601, UTC, with milliseconds and `Z`
- `service`: the service name (see Section 4.1)
- `level`: one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `message`: human readable text
- `extra`: optional object with any extra fields

### 3.2 Metrics each service exposes at `/metrics`
Use the Prometheus client library. Metric names (keep them identical across services):

| Metric | Type | Meaning |
|---|---|---|
| `http_requests_total{service, endpoint, status}` | counter | requests handled |
| `http_request_duration_seconds{service, endpoint}` | histogram | request latency |
| `app_errors_total{service}` | counter | application errors logged |
| `app_memory_bytes{service}` | gauge | current process memory |
| `app_up{service}` | gauge | 1 when healthy |

Container-level metrics (CPU, memory limit, restarts) come from cAdvisor (see Section 5).

### 3.3 MCP tools you will provide (Weeks 1 to 2)
Tool names and shapes. Do not rename them without telling Person A.

```
get_metrics(service: str, metric: str, minutes: int = 5) -> {
    "service": str, "metric": str, "window_minutes": int,
    "latest": float | null, "min": float | null, "max": float | null,
    "samples": [[unix_ts, value], ...]
}

get_pod_status(service: str) -> {
    "service": str, "state": "running|restarting|exited|oom_killed|unhealthy|not_found",
    "restart_count": int, "exit_code": int | null,
    "oom_killed": bool, "health": "healthy|unhealthy|none",
    "started_at": str | null, "memory_limit_mb": int | null
}

get_events(service: str, minutes: int = 15) -> {
    "service": str,
    "events": [{"timestamp": str, "type": str, "reason": str, "message": str}]
}
```

### 3.4 Incident log + ground truth files
Each failure you capture produces TWO files in `data/incident_logs/`:
- `<scenario_id>.jsonl`: the captured logs (JSON Lines as above)
- `<scenario_id>.meta.json`: ground truth, used later by the benchmark:

```json
{
  "scenario_id": "oom-payment-001",
  "service": "payment-service",
  "failure_type": "out_of_memory",
  "root_cause": "Container memory limit (64MB) too low; /leak endpoint allocates unbounded memory",
  "expected_fix": "Raise memory limit to 256MB and fix the leak",
  "signals": ["oom_killed=true", "exit_code=137", "restart_count increasing", "memory near limit"],
  "how_to_reproduce": "python infra/failures/oom.py"
}
```

---

## 4. WEEK 1 (Days 2 to 7): your tasks in detail

Goal for the end of Week 1: you can run one command to bring up three sample services plus Prometheus and Grafana, run one command to break a service on purpose, and have the logs and ground-truth saved. You do NOT need to connect to Person A's agent this week.

### Task B1 (Days 2 to 3): Sample microservices

Create `sample_apps/` with three small FastAPI services:

| Service | Purpose | Port |
|---|---|---|
| `payment-service` | accepts payments, talks to Postgres | 8001 |
| `order-service` | creates orders, calls payment-service over HTTP | 8002 |
| `inventory-service` | stock checks, talks to Postgres | 8003 |

Plus one `postgres` container (in compose).

Structure per service:

```
sample_apps/payment-service/
├── app/
│   ├── main.py           (FastAPI app, routes)
│   ├── logging_config.py (JSON logger, see contract 3.1)
│   ├── metrics.py        (prometheus_client metrics, see contract 3.2)
│   └── faults.py         (fault toggles, see below)
├── Dockerfile
├── requirements.txt      (only for this service, inside its own folder)
└── README.md
```

Each service must have:
- `GET /health` returns 200 `{"status":"ok"}` normally; returns 500 when the health fault is on.
- `GET /metrics` Prometheus metrics.
- A couple of realistic endpoints (e.g. `POST /pay`, `POST /orders`, `GET /stock/{item}`) that do small real work (simple DB read/write) and log every request and every error as JSON.
- `GET /leak` (only needs to exist in `payment-service`): allocates ~10 MB more memory per call and keeps it. Used for the OOM scenario.
- **Configuration only through environment variables**: `DATABASE_URL`, `PAYMENT_SERVICE_URL`, `SERVICE_NAME`, `LOG_LEVEL`. If a required variable is missing, the app must log a clear CRITICAL error and exit with code 1 (this is the "bad env var" failure).
- **Fault toggles** (in `faults.py`), controllable at runtime via `POST /admin/fault` with body like `{"health_fail": true}` and also by env var at startup. Keep it small: `health_fail`, `slow_db` (adds a delay), `db_error`.

Acceptance check for B1:
- `docker build` works for each service, and `docker run` serves `/health` and `/metrics`.
- Hitting an endpoint produces a JSON log line that exactly matches contract 3.1.
- `curl localhost:8001/metrics` shows the metric names from contract 3.2.

### Task B2 (Days 3 to 4): docker-compose + monitoring stack

Create `infra/docker-compose.yml` with:
- the 3 services + `postgres`
- `prometheus` (config at `infra/prometheus/prometheus.yml`, scraping each service's `/metrics` every 5s)
- `grafana` (provisioned datasource at `infra/grafana/provisioning/`, plus one dashboard JSON with: request rate, error rate, memory per service, container restarts)
- `cadvisor` (container CPU / memory / restart metrics, scraped by Prometheus)
- a load generator: a tiny script/container `infra/loadgen/` that sends steady traffic (a request or two per second) to the services so graphs have data

Important details:
- Give each service a `mem_limit` in compose (`payment-service: 128m` is fine as default; the OOM scenario will lower it).
- Add a `healthcheck` for each service in compose that calls `/health`.
- Use `restart: unless-stopped` so crashes show up as restarts.
- Put DB credentials in `.env.infra.example` (committed, fake values) and `.env` (not committed).

Acceptance check for B2:
- `docker compose -f infra/docker-compose.yml up -d` brings everything up.
- Prometheus (`localhost:9090`) shows all targets as UP.
- Grafana (`localhost:3000`) shows the dashboard with live data.
- In Prometheus, the query `app_errors_total` and a cAdvisor memory metric both return data.

### Task B3 (Days 5 to 6): Failure injection (3 scenarios) + log capture

Create `infra/failures/` with one script per scenario (Python or bash, your choice, keep it simple). Each script should: (1) make sure the stack is healthy, (2) inject the failure, (3) wait for the symptoms, (4) capture logs into `data/incident_logs/`, (5) write the `.meta.json` ground-truth file (contract 3.4), (6) print how to restore.

Scenarios:

1. **`oom.py` (out of memory):** restart `payment-service` with a very low memory limit (e.g. 64m), then call `/leak` repeatedly until the container is OOM-killed and restarts. Symptoms: exit code 137, `OOMKilled=true`, restart count rising, memory metric near limit.
2. **`bad_env.py` (misconfiguration):** restart `order-service` with `PAYMENT_SERVICE_URL` removed or `DATABASE_URL` malformed. Symptoms: CRITICAL log about the missing config, exit code 1, crash loop.
3. **`health_fail.py` (failed health check):** turn on `health_fail` for `inventory-service` via `/admin/fault`. Symptoms: Docker health status becomes `unhealthy`, `/health` returns 500, `app_up` drops.

Log capture: use `docker compose logs --no-log-prefix --since <time> <service>` and also keep only valid JSON lines. Save Docker inspect info (state, exit code, OOMKilled, restart count) into the `.meta.json` `signals` list.

Also create `infra/failures/restore.sh` that returns everything to a healthy state.

Acceptance check for B3:
- Running each script produces `<scenario_id>.jsonl` and `<scenario_id>.meta.json` in `data/incident_logs/`.
- The `.meta.json` has a clear root cause and expected fix.
- `restore.sh` brings the stack back to healthy.

### Task B4 (Day 7): Documentation and handoff to Person A

Write `docs/infra.md` containing:
- how to start the stack, how to stop it
- list of services, ports, metrics
- how to reproduce each failure and how to restore
- example Prometheus queries that are useful for diagnosis (memory, restarts, error rate)
- what the captured incident files contain

Then tell Person A: "The logs and ground-truth files are in `data/incident_logs/`, and here is how to start the stack." She can use them to write runbooks that match your real failures.

### Week 1 definition of done
- [ ] 3 services run with JSON logs and `/metrics`
- [ ] One command starts services + Prometheus + Grafana + cAdvisor + load generator
- [ ] 3 failure scripts work and produce log + ground-truth files
- [ ] `docs/infra.md` written
- [ ] Everything merged to `main` through PRs

---

## 5. Useful implementation hints (for the IDE agent)

- Python libs for services: `fastapi`, `uvicorn`, `prometheus-client`, `psycopg2-binary` (or `asyncpg`), `httpx`, `python-json-logger` (or a small custom JSON formatter).
- Memory gauge: `psutil.Process().memory_info().rss`.
- Detect OOM kill: `docker inspect <container> --format '{{.State.OOMKilled}} {{.State.ExitCode}} {{.RestartCount}}'`.
- cAdvisor gives `container_memory_usage_bytes`, `container_spec_memory_limit_bytes`, `container_cpu_usage_seconds_total`. Restart counts are easiest from `docker inspect`, which is also what the Week 2 `get_pod_status` tool will use.
- If Docker on Windows/Mac behaves differently for cAdvisor, fall back to the Docker SDK for container stats and say so in `docs/infra.md`.

---

## 6. WEEK 2 (Days 8 to 14): preview

Goal: your tools exist as MCP servers and connect to Person A's agent.

| Days | Task |
|---|---|
| 8 | Add 2 to 3 more failure scenarios with the same log + ground-truth outputs: DB connection timeout (`slow_db`/`db_error`), dependency failure (order-service cannot reach payment-service), disk full or CPU saturation. Update `docs/infra.md` |
| 9 to 10 | `mcp_servers/prometheus/`: build the `get_metrics` MCP server with the Python MCP SDK (FastMCP). It queries Prometheus's HTTP API (`/api/v1/query_range`). Return the shape in contract 3.3. Add input validation and clear errors when the service or metric does not exist |
| 11 | `mcp_servers/kubernetes/`: build `get_pod_status` and `get_events` using the Docker SDK for now (Minikube comes in Week 3). Keep the same output shape so swapping to Kubernetes later does not change the agent |
| 12 | Test each MCP server on its own with MCP Inspector or a small script. Write `README.md` in each server folder with how to run and example calls |
| 13 to 14 | Integrate with Person A: she connects the agent to your servers. Break a service live and check the agent diagnoses it. Fix bugs in small PRs. Record a short demo video as a fallback |

Week 2 definition of done: from the CLI, "why is payment-service failing?" produces a diagnosis using runbooks plus your live metrics and pod status.

---

## 7. WEEKS 3 to 5: roadmap (details will be refined later)

### Week 3: Kubernetes, Slack, CI/CD
- Move the stack to **Minikube** (or kind): write k8s manifests in `infra/k8s/` (Deployments, Services, resource limits, probes). Update `get_pod_status` / `get_events` to use the Kubernetes API behind the same output shape.
- **Slack bot** in `interfaces/slack/` with Slack Bolt: mention the bot or use a slash command, forward the question to the agent, post the answer with sources. Use a free test workspace.
- **GitHub Actions** CI/CD: lint and test on every PR, build Docker images, optional deploy to Minikube.

### Week 4: Smarter diagnosis support and chaos benchmark
- **"What changed?" tool:** a GitHub MCP server (recent commits, CI runs, image tag changes) so the agent can correlate failures with recent changes.
- **Chaos testing:** use LitmusChaos or Chaos Mesh (or simple scripted chaos) to inject faults automatically.
- **Benchmark harness** in `infra/benchmark/`: for each scenario, inject the fault, ask the agent, compare its answer with the `.meta.json` ground truth, and record accuracy, time to diagnosis, and cost.

### Week 5: Safe remediation, final polish
- **Remediation MCP server:** actions like restart, scale, rollback, raise memory limit. Read-only by default. Write actions go through a **policy file** (allow/deny YAML), always do a **dry-run first**, require **human approval** (Slack button), and write an **audit log**.
- **Verification and rollback:** after an approved fix, watch Prometheus for a few minutes and roll back automatically if things got worse.
- Run the final benchmark, write your sections of the project report, and prepare the demo.

If time gets tight, cut in this order: self-learning runbooks, then "what changed?", then auto-rollback. Keep the chaos benchmark and approval-gated remediation, since they are what make the project stand out.

---

## 8. First message to send to your IDE agent

> Read PERSON_B_BRIEF.md fully. I am Person B. We are doing Week 1 only. Start with Task B1 (sample microservices). Create the folder structure, then build `payment-service` first and show me how to run and verify it before building the other two. Follow the folder ownership and git rules strictly and do not touch Person A's folders.
