#!/usr/bin/env bash
# ChatOps repo bootstrap. Run ONCE by Person A on Day 1.
#
# Usage:
#   bash setup_repo.sh path/to/your/cloned/repo
#
# It creates the folder skeleton, .gitignore, the shared contracts, per-person
# requirement/env files, and copies PERSON_A_BRIEF.md and PERSON_B_BRIEF.md
# (if they sit next to this script) into the repo root.
# It does NOT commit or push. You do that yourself (see the checklist).

set -euo pipefail

REPO_DIR="${1:-chatops-agent}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$REPO_DIR"
cd "$REPO_DIR"
[ -d .git ] || git init -b main >/dev/null

# ---------- folder skeleton (each empty folder gets a .gitkeep) ----------
DIRS=(
  agent
  rag
  mcp_servers/runbooks
  mcp_servers/prometheus
  mcp_servers/kubernetes
  interfaces/cli
  interfaces/slack
  sample_apps
  infra
  data/runbooks
  data/incident_logs
  contracts
  docs
)
for d in "${DIRS[@]}"; do
  mkdir -p "$d"
  [ -e "$d/.gitkeep" ] || touch "$d/.gitkeep"
done

# ---------- .gitignore ----------
cat > .gitignore <<'EOF'
# secrets
.env
.env.*
!.env.*.example

# python
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/

# local data stores / logs
chroma_db/
*.log

# IDE / OS
.idea/
.vscode/
.DS_Store
EOF
# NOTE: data/incident_logs/*.jsonl and *.meta.json are intentionally NOT ignored.

# ---------- per-person dependency + env files (avoid shared-file conflicts) ----------
cat > requirements-agent.txt <<'EOF'
# Person A (agent + RAG). Add pinned versions as you install them.
langchain
langchain-core
langchain-community
langchain-aws
langchain-ollama
langchain-huggingface
langgraph
chromadb
sentence-transformers
python-frontmatter
pyyaml
mcp
typer
rich
python-dotenv
EOF

cat > requirements-infra.txt <<'EOF'
# Person B (sample apps, tools, infra). Add pinned versions as you install them.
fastapi
uvicorn
prometheus-client
psutil
httpx
docker
mcp
python-dotenv
EOF

cat > .env.agent.example <<'EOF'
# Person A. Copy to .env.agent and fill in. NEVER commit the real file.
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
# Optional: use a named profile instead of keys
AWS_PROFILE=
LLM_PROVIDER=bedrock          # bedrock | ollama
OLLAMA_BASE_URL=http://localhost:11434
EOF

cat > .env.infra.example <<'EOF'
# Person B. Copy to .env and fill in. NEVER commit the real file.
POSTGRES_USER=chatops
POSTGRES_PASSWORD=change_me
POSTGRES_DB=chatops
PROMETHEUS_URL=http://localhost:9090
EOF

# ---------- README (Person A owns it) ----------
cat > README.md <<'EOF'
# ChatOps: AI-Powered SRE Agent

An open-source agent that diagnoses deployment failures. An engineer asks
"why did payment-service fail?" and the agent searches runbooks (RAG), pulls live
metrics and container status through MCP tools, and answers with a cited diagnosis.

## Team
- Person A: LLM, RAG, agent, CLI, runbook MCP server
- Person B: sample services, monitoring, failure injection, metrics and status MCP servers, Slack, CI/CD

## Layout
See PERSON_A_BRIEF.md and PERSON_B_BRIEF.md for folder ownership and tasks.
Shared formats live in `contracts/`. Infra docs: `docs/infra.md`. Agent docs: `docs/agent.md`.

## Quick start
(Person A fills this in as the project grows.)
EOF

# ---------- contracts ----------
cat > contracts/README.md <<'EOF'
# Contracts (shared, frozen after Day 1)

These files define how Person A's code and Person B's code fit together.
Changing anything here needs its own PR that BOTH people approve.

- logs.md: JSON log line format
- metrics.md: Prometheus metric names
- mcp_tools.md: MCP tool names, inputs and outputs
- runbook_format.md: runbook Markdown format
- failure_types.md: the shared list of failure_type values
- incident_meta.md: ground-truth file written for every captured incident
EOF

cat > contracts/logs.md <<'EOF'
# Log format: JSON Lines

Every sample service writes one JSON object per line to stdout:

```json
{"timestamp": "2026-10-12T10:15:30.123Z", "service": "payment-service", "level": "ERROR", "message": "Database connection timed out after 5s", "extra": {"request_id": "abc123"}}
```

| Field | Rule |
|---|---|
| timestamp | ISO 8601, UTC, milliseconds, trailing `Z` |
| service | payment-service, order-service or inventory-service |
| level | DEBUG, INFO, WARNING, ERROR or CRITICAL |
| message | human readable text |
| extra | optional object |
EOF

cat > contracts/metrics.md <<'EOF'
# Prometheus metrics exposed at /metrics by each sample service

| Metric | Type | Meaning |
|---|---|---|
| http_requests_total{service, endpoint, status} | counter | requests handled |
| http_request_duration_seconds{service, endpoint} | histogram | request latency |
| app_errors_total{service} | counter | application errors logged |
| app_memory_bytes{service} | gauge | process memory (RSS) |
| app_up{service} | gauge | 1 when healthy |

Container metrics (CPU, memory usage and limit) come from cAdvisor.
EOF

cat > contracts/mcp_tools.md <<'EOF'
# MCP tools

Do not rename tools or change shapes without a contract PR approved by both people.

## Person B provides

```
get_metrics(service: str, metric: str, minutes: int = 5) -> {
  "service": str, "metric": str, "window_minutes": int,
  "latest": float|null, "min": float|null, "max": float|null,
  "samples": [[unix_ts, value], ...]
}

get_pod_status(service: str) -> {
  "service": str,
  "state": "running|restarting|exited|oom_killed|unhealthy|not_found",
  "restart_count": int, "exit_code": int|null, "oom_killed": bool,
  "health": "healthy|unhealthy|none",
  "started_at": str|null, "memory_limit_mb": int|null
}

get_events(service: str, minutes: int = 15) -> {
  "service": str,
  "events": [{"timestamp": str, "type": str, "reason": str, "message": str}]
}
```

## Person A provides

```
search_runbooks(query: str, top_k: int = 3) -> {
  "query": str,
  "results": [
    {"title": str, "source": str, "failure_type": str, "service": str,
     "score": float, "snippet": str}
  ]
}
```

Errors: tools return `{"error": "<clear message>"}` instead of raising, so the
agent can read the problem and react.
EOF

cat > contracts/runbook_format.md <<'EOF'
# Runbook format

One Markdown file per failure in `data/runbooks/`, named `<failure_type>-<short-name>.md`.

```markdown
---
title: "OOMKilled: Diagnosis and Fix"
failure_type: out_of_memory
service: payment-service
severity: high
---

## Symptoms
## Likely cause
## How to confirm
## Fix
## Prevention
```

- `failure_type` must come from `failure_types.md`
- `service` is a service name, or `any` for generic runbooks
EOF

cat > contracts/failure_types.md <<'EOF'
# Shared failure_type values

Used in runbook front-matter AND in incident `.meta.json` files.

- out_of_memory
- bad_config
- health_check_failure
- db_timeout
- dependency_failure
- disk_full
- cpu_saturation
EOF

cat > contracts/incident_meta.md <<'EOF'
# Incident ground truth

Every captured failure in `data/incident_logs/` has two files:
`<scenario_id>.jsonl` (logs, see logs.md) and `<scenario_id>.meta.json`:

```json
{
  "scenario_id": "oom-payment-001",
  "service": "payment-service",
  "failure_type": "out_of_memory",
  "root_cause": "Memory limit (64MB) too low; /leak allocates unbounded memory",
  "expected_fix": "Raise memory limit to 256MB and fix the leak",
  "signals": ["oom_killed=true", "exit_code=137", "restart_count increasing"],
  "how_to_reproduce": "python infra/failures/oom.py"
}
```

Used by Person A to write matching runbooks and by the Week 4 benchmark to score the agent.
EOF

# ---------- empty doc stubs ----------
[ -e docs/agent.md ] || printf '# Agent and RAG notes (Person A)\n' > docs/agent.md
[ -e docs/infra.md ] || printf '# Infra notes (Person B)\n' > docs/infra.md

# ---------- copy briefs if present ----------
for f in PERSON_A_BRIEF.md PERSON_B_BRIEF.md; do
  [ -f "$HERE/$f" ] && cp "$HERE/$f" "./$f"
done

echo
echo "Done. Repo skeleton created in: $(pwd)"
echo "Next: review with 'git status', then commit and push to main (see checklist)."
