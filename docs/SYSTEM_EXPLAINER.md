# ChatOps SRE Agent: The Complete Architectural & Operational Explainer

> **How to use this document:**  
> This guide is designed to explain **everything** about the system from first principles to a friend, fellow software engineer, or technical interviewer. It covers the problem, the core architecture, the technical integrations, how surprise failures are diagnosed without playbooks, the safety boundaries, the continuous learning loop, and empirical benchmarks.

---

## Table of Contents
1. [The Problem & The Vision](#1-the-problem--the-vision)
2. [High-Level Architecture (The Two-Brain Design)](#2-high-level-architecture-the-two-brain-design)
3. [The Secret Sauce: The "Evidence-First" Protocol](#3-the-secret-sauce-the-evidence-first-protocol)
4. [How We Integrated Everything (The Technical Plumbing)](#4-how-we-integrated-everything-the-technical-plumbing)
5. [How Surprise & Novel Failures Are Handled](#5-how-surprise--novel-failures-are-handled)
6. [Supported Incidents, Failure Types & Runbooks](#6-supported-incidents-failure-types--runbooks)
7. [The Remediation Safety Engine & Auto-Rollback](#7-the-remediation-safety-engine--auto-rollback)
8. [The Continuous Learning Loop (From Postmortem to Playbook)](#8-the-continuous-learning-loop-from-postmortem-to-playbook)
9. [Empirical Results & Proof Points (The Brag Sheet)](#9-empirical-results--proof-points-the-brag-sheet)
10. [End-to-End Walkthrough of a Real Incident](#10-end-to-end-walkthrough-of-a-real-incident)

---

## 1. The Problem & The Vision

### The SRE Nightmare
When microservices go down at 2 AM, the modern Site Reliability Engineering (SRE) workflow is frantic:
1. PagerDuty sounds an alarm.
2. Engineers scramble across 5 browser tabs: Grafana dashboards, Datadog/Prometheus metrics, Kubernetes pod states, Elasticsearch/Loki logs, and Notion/Confluence runbooks.
3. Teams suffer from **high MTTR (Mean Time to Resolution)**, alert fatigue, and cognitive overload.
4. Outdated, stale runbooks lead to incorrect manual interventions that often exacerbate outages.

### Why Simple LLM Wrappers Fail
Many teams try building an "AI SRE" by simply sending Prometheus alerts to ChatGPT. This fails catastrophically:
- **Hallucinated Metrics**: An LLM will invent CPU percentages or fake log lines that don't exist.
- **Confirmation Bias ("RAG-First" Trap)**: If a user asks *"why is payment-service down with OOM?"*, a naive RAG bot searches OOM playbooks immediately and diagnoses an OOM error, even if the service actually crashed because of a missing database password!
- **Dangerous Blind Mutations**: LLMs given direct shell or `kubectl` access can accidentally execute destructive actions (`rm -rf`, `DROP TABLE`, or restart the wrong database).
- **Novel Failure Paralysis**: When an incident has no pre-written company runbook, standard RAG agents freeze, hallucinate, or cite irrelevant playbooks.

### Our Solution
We built an **Evidence-First AI SRE Agent** that acts as an autonomous tier-1 incident responder:
- It **never trusts user assumptions**.
- It **interrogates live telemetry first** (Docker/Kubernetes status, exit codes, recent error logs, Prometheus rate metrics, deployment diffs) before it ever touches a playbook.
- It operates under a strict **Human-in-the-Loop Safety Boundary**: the agent can only propose dry-run fixes; mutations require single-use cryptographic approval in Slack.
- If a proposed fix degrades system health, an **automatic rollback engine** immediately restores previous stability.

---

## 2. High-Level Architecture (The Two-Brain Design)

The system is decoupled into two communicating halves via the **Model Context Protocol (MCP)**:
- **Person A (The Brain / Agent)**: Reasoning state machine, foundation model, conversation memory, dual RAG collections.
- **Person B (The Body / Infra & MCP Tools)**: Microservice application stack, chaos injection engine, Prometheus observability, and MCP tool servers.

```
+---------------------------------------------------------------------------------------+
|                                    USER INTERFACES                                    |
|              Slack Bot (Socket Mode / Block Kit)   |   ChatOps CLI (Terminal)        |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                  THE AGENT BRAIN                                      |
|                                                                                       |
|   +-------------------------------------------------------------------------------+   |
|   |                      LangGraph ReAct State Machine                            |   |
|   |   - Foundation Models: AWS Bedrock Qwen3 VL 235B / Mistral Large 3 / DeepSeek |   |
|   |   - MemorySaver: Thread-safe multi-turn context keyed by thread_id            |   |
|   +---------------------------------------+---------------------------------------+   |
|                                           |                                           |
|                     Hard Python Gate: evidence_gate.py                                |
|           (Blocks search_runbooks until pod status + logs are retrieved)             |
|                                           |                                           |
|     +-------------------------------------+-------------------------------------+     |
|     |                                                                           |     |
|     v                                                                           v     |
|  [ Internal Runbooks ]                                                [ External Knowledge ]  |
|  10 Curated Company Playbooks                                          105 Public Postmortems |
|  (Chroma collection: internal_runbooks)                                (Chroma collection:    |
|  *Boosted +0.03 in ranking*                                             external_knowledge)   |
+-------------------------------------------+-------------------------------------------+
                                            |
                         Model Context Protocol (MCP) Tools
                                            |
     +-----------------+--------------------+--------------------+-----------------+
     |                 |                    |                    |                 |
     v                 v                    v                    v                 v
[ MCP Kubernetes ] [ MCP Prometheus ] [ MCP Changes ]    [ MCP Runbooks ]  [ MCP Remediation ]
- get_pod_status   - get_metrics      - what_changed     - search_runbooks - propose_remediation
- get_logs         - get_anomalies                                         - apply_remediation
- get_events       (15s scrape rate)                                       (Single-use token)
     |                 |                    |                                      |
+----+-----------------+--------------------+--------------------------------------+----+
|                             LIVE DOCKER COMPOSE STACK                                 |
|                                                                                       |
|   +-------------------+     +------------------+     +----------------------------+   |
|   |  payment-service  | <-> |  order-service   | <-> |     inventory-service      |   |
|   |  (Port 8001)      |     |  (Port 8002)     |     |     (Port 8003)            |   |
|   +---------+---------+     +--------+---------+     +-------------+--------------+   |
|             |                        |                             |                  |
|             v                        v                             v                  |
|   +-------------------+     +------------------+     +----------------------------+   |
|   |    PostgreSQL     |     | Toxiproxy Engine |     |    cAdvisor + Prometheus   |   |
|   |    Database       |     | (Network Jitter) |     |    (Cluster Telemetry)     |   |
|   +-------------------+     +------------------+     +----------------------------+   |
+---------------------------------------------------------------------------------------+
```

---

## 3. The Secret Sauce: The "Evidence-First" Protocol

### Why "RAG-First" Fails
In traditional RAG systems, the moment a user asks a question, the vector database retrieves the closest matching runbook. If an alert says `"Payment timeout"`, the agent immediately reads the *"Database Timeout"* runbook. It then hallucinates or cherry-picks logs to fit that diagnosis.

### How Evidence-First Works
Our agent enforces an **Evidence-First Code Gate** (`mcp_servers/runbooks/evidence_gate.py`):
1. The tool `search_runbooks` is **hard-blocked** by a Python runtime gate at the start of every diagnosis.
2. If the LLM tries to call `search_runbooks` prematurely, the tool returns:
   ```json
   {"error": "gather evidence first: inspect pod status and logs for <service> before consulting runbooks"}
   ```
3. The LLM is forced to follow this strict diagnostic order:
   - **Step 1: Check Pod Status (`get_pod_status`)**  
     Queries container lifecycle state, cgroup memory limits, Docker exit codes (137 = OOM, 1 = crash, 0 = clean stop), and restart counts.
   - **Step 2: Collect Error Logs (`get_logs`)**  
     Extracts raw structured logs filtering for `ERROR` and `CRITICAL` levels.
   - **Step 3: Collect Telemetry & Metrics (`get_metrics`, `get_anomalies`)**  
     Queries Prometheus for p95 latency spikes, CPU throttling, error rate percentages, and memory growth slopes.
   - **Step 4: Check Deploys (`what_changed`)**  
     Correlates the incident timestamp against git commits and deployment manifests.
   - **Step 5: Consult Runbooks (`search_runbooks`)**  
     Only *after* the evidence is gathered can the agent query the vector store, using observed facts (e.g., `exit code 137 memory exceeded`) as the search query.
   - **Step 6: Formulate Remediation (`propose_remediation`)**  
     Generates a safe dry-run fix requiring human sign-off.

---

## 4. How We Integrated Everything (The Technical Plumbing)

### 1. The Microservice Application Stack
- **`order-service`**: Core checkout orchestrator. Communicates with `payment-service` and Postgres.
- **`payment-service`**: Handles transactions, holds in-memory allocation buffers, and talks to Postgres.
- **`inventory-service`**: Manages stock items, writes warehouse payload files to local disk.
- **`postgres`**: Relational database storage shared by the services.
- **`toxiproxy`**: Layer-7 TCP proxy simulator allowing us to inject packet loss, latency (e.g. 3000ms delay), and socket timeouts on network paths.

### 2. Observability Pipeline
- **Prometheus**: Scrapes metrics every 15 seconds from `/metrics` endpoints.
- **cAdvisor**: Collects real-time container-level cgroup metrics (CPU usage, memory limits, network I/O).
- **Structured JSON Logging**: Every microservice emits logs as JSON lines with timestamp, service name, log level, and message payload.

### 3. Model Context Protocol (MCP) Servers
Tools are implemented as standard MCP endpoints exposing strict JSON schemas:
- `mcp_servers/kubernetes/`: Interrogates Docker/K8s container runtime.
- `mcp_servers/prometheus/`: Queries Prometheus range queries and rate metrics.
- `mcp_servers/runbooks/`: Vector search over Chroma collections.
- `mcp_servers/remediation/`: Proposes, hashes, and applies operational remediations.

### 4. Foundation Model Engine
- Primary model: **Qwen3 VL 235B** via AWS Bedrock Converse API (`us-east-1`).
- Fallbacks: **Mistral Large 3**, **DeepSeek V3.2**, and **Kimi K1.5**.
- **Reasoning-Leak Sanitizer**: Regex filters ensure that internal `<think>` scratchpads from deep-reasoning models are stripped before user presentation.

### 5. Multi-Turn Slack Bot (Socket Mode)
- Built with Slack Bolt for Python.
- Operates over **Socket Mode** using `xapp-...` app tokens (zero public firewall ingress required).
- Preserves conversation history across Slack threads via LangGraph `thread_id=thread_ts`.
- Emits interactive **Block Kit cards** containing diagnostic headers, confidence meters, tools used, sources, and interactive `Approve` / `Reject` buttons.

---

## 5. How Surprise & Novel Failures Are Handled

A **"Surprise Failure"** is an incident for which **no internal company runbook exists**. In conventional systems, this leads to complete hallucination. Here is how our architecture solves it:

### 1. Ground Truth from Telemetry, Not Playbooks
Because the agent is gated to read telemetry first, it diagnoses what is *physically happening* on the machine, not what a playbook told it to expect.
- In **Surprise 1 (`surprise_1.py`)**, we started `order-service` with an invalid database password (`DATABASE_URL=...WRONG_PASSWORD_XYZ...`).
- There is **no runbook** for database passwords in `data/runbooks/`.
- The agent called `get_logs` and extracted:
  `FATAL: password authentication failed for user "chatops"`
- It immediately diagnosed: `"The order-service cannot connect to PostgreSQL due to invalid database credentials"`, despite having zero runbooks.

### 2. Dual-Collection Chroma Architecture
We separate internal company playbooks from external real-world incident postmortems using two isolated Chroma collections:

```
[ Vector Search Engine ]
       |
       +---> Collection 1: `internal_runbooks` (10 playbooks, 62 chunks)
       |     - Curated internal company standard operating procedures.
       |     - Receives a +0.03 score tie-breaker boost.
       |
       +---> Collection 2: `external_knowledge` (105 public incidents, 430 chunks)
             - Real public postmortems (Target, Monzo, Cloudflare, Kubernetes GitHub issues).
             - Returns public URLs (`https://...`).
             - Framed as: "External Postmortem / Similar Incident", never as internal instruction.
```

If an internal playbook matches, it wins. If no internal playbook matches, the agent falls back to external postmortems to provide engineers with historical public precedent.

### 3. Confidence Fallback (`no_confident_match`)
Every vector search computes cosine similarity. If the top hit scores below **0.60**, the system sets:
```json
{"no_confident_match": true, "results": []}
```
The agent honestly reports: `Failure Type: unknown` and states: *"No confident runbook match found — manual investigation required"*. It **refuses to hallucinate**.

---

## 6. Supported Incidents, Failure Types & Runbooks

### The 10 Canonical Chaos Scenarios
Our system was tested and evaluated against 10 reproducible failure scenarios in `infra/failures/`:

| # | Scenario ID | Target Service | Injected Root Cause | What the Agent Detects | Expected Remediation |
|:---|:---|:---|:---|:---|:---|
| **1** | `oom-payment-001` | `payment-service` | Constrained memory (64MB) + `/leak` endpoint allocating 10MB chunks. | Kernel exit code 137 (SIGKILL), `oom_killed: true`. | Propose `set_memory_limit` to 256MB. |
| **2** | `badenv-order-001` | `order-service` | Startup without required `PAYMENT_SERVICE_URL`. | Exit code 1, missing environment variable in stderr. | Refuses memory fix; suggests setting env var. |
| **3** | `healthfail-inventory-001` | `inventory-service` | Fault toggle `/admin/fault` returning HTTP 500 on `/health`. | Container health status: `unhealthy`. | Restarts service or clears fault toggle. |
| **4** | `dbtimeout-payment-001` | `payment-service` | Injected 3-second database query delay via `slow_db`. | Anomaly: 527% p95 latency spike (peak 621ms). | Identifies downstream DB latency; safe dry-run. |
| **5** | `depfail-order-001` | `order-service` | `payment-service` stopped; checkout returns HTTP 502. | Unreachable upstream dependency in logs. | Proposes `restart_service` on `payment-service`. |
| **6** | `cpusat-payment-001` | `payment-service` | Tight compute loop on `/burn` saturating 0.5 CPU quota. | Latency spikes + `/burn completed` warnings in logs. | Proposes scaling CPU limits or killing burn task. |
| **7** | `diskfull-inventory-001` | `inventory-service` | `/fill` endpoint writes 1.9GB payload to `/tmp`. | `[Errno 28] No space left on device` in logs. | Calls `/fill/reset` or removes temp file. |
| **8** | `nettimeout-order-001` | `order-service` | Toxiproxy injects 3000ms delay between order & payment. | Socket timeout and TCP connection refused. | Suggests resetting Toxiproxy / checking network. |
| **9** | `baddeploy-order-001` | `order-service` | Deploy event logged right before 50% error rate spike. | `what_changed` correlates deploy with error spike. | Proposes `rollback_deploy` to previous image. |
| **10**| `crashloop-payment-001` | `payment-service` | Broken CMD command causing immediate exit 1 & restart. | Rapidly incrementing restart count (>3) & exit code 1. | Reverts command and restarts healthy container. |

### The Unseen Surprise Scenarios
- **`surprise_1.py`**: Postgres authentication failure (wrong database password).
- **`surprise_2.py`**: Postgres connection pool saturation (150 concurrent client threads).

### The Internal Runbook Library (`data/runbooks/`)
1. `runbook-oom-payment.md`: Out of Memory handling.
2. `runbook-bad-env-order.md`: Missing environment variables.
3. `runbook-health-check-inventory.md`: Unhealthy probe diagnosis.
4. `runbook-db-timeout-payment.md`: Slow database query remediation.
5. `runbook-dep-failure-order.md`: Downstream dependency failure handling.
6. `runbook-cpu-saturation-payment.md`: CPU throttling resolution.
7. `runbook-disk-full-inventory.md`: Disk cleanup procedures.
8. `runbook-network-timeout-order.md`: Network delay and socket retry policies.
9. `runbook-bad-deploy-order.md`: Rollback procedures.
10. `runbook-crash-loop-payment.md`: CrashLoopBackOff triage.

---

## 7. The Remediation Safety Engine & Auto-Rollback

### The Golden Rule of Safety
**The agent is strictly prohibited from mutating infrastructure on its own.**  
There is no `apply_remediation` tool in the agent's schema. The LLM can only call `propose_remediation`.

### The 4-Step Cryptographic Safety Chain

```
[ Agent Diagnoses Issue ]
           |
           v
1. `propose_remediation(service, action, params)`
   - Computes SHA-256 hash of parameters: param_hash = SHA256(action + service + params)
   - Generates single-use approval_token = UUID4()
   - Generates proposal_id = UUID4()
   - Stores {token, param_hash, allowed_approvers} in secure server memory (_PROPOSALS)
   - Returns ONLY dry-run changes and risk level (token is NEVER leaked to the LLM!)
           |
           v
2. [ Slack Interactive Block Kit Card ]
   - Shows action, risk level, and two buttons: [ ✅ Approve & Apply ] and [ ❌ Reject ]
   - Embeds proposal_id into the button payload.
           |
           v
3. Human Engineer Clicks [ ✅ Approve & Apply ]
   - Checks user Slack ID against APPROVER_SLACK_IDS (Role-Based Access Control).
   - Validates that proposal_id exists and has not expired (300s TTL).
   - Verifies that approval_token has NOT been previously used (Replay attack defense).
   - Verifies that parameters match the original SHA-256 param_hash (Tampering defense).
   - Marks token as USED=True.
   - Executes mutation via Docker API.
   - Logs event to data/audit_log.jsonl with cryptographic audit_id.
           |
           v
4. Background Post-Fix Verification (30 Seconds)
   - Spawns background thread watching container health and error metrics.
   - IF metrics improve: Posts ✅ Verification: Improved in Slack thread.
   - IF metrics degrade or container crashes:
     -> Triggers immediate automatic rollback (_rollback_action).
     -> Reverts container to previous memory/image state.
     -> Posts 🔄 Verification: Rolled Back in Slack thread.
     -> If rollback fails: Permanently locks service in _BLOCKED_SERVICES.
```

---

## 8. The Continuous Learning Loop (From Postmortem to Playbook)

When an engineering team resolves a novel incident, how does the agent learn without retraining the model?

```
      +-------------------------------------------------------------+
      |               Incident Resolved by Human SRE                |
      +------------------------------+------------------------------+
                                     |
                                     v
      +-------------------------------------------------------------+
      |  1. chatops learn "<notes from resolved incident>"          |
      |     - LLM synthesizes structured Markdown playbook          |
      |     - Creates file in data/runbooks/drafts/                 |
      +------------------------------+------------------------------+
                                     |
                                     v
      +-------------------------------------------------------------+
      |  2. Strict Quarantine                                       |
      |     - Drafts are NOT indexed in Chroma                      |
      |     - Vector searches return 0 hits for draft playbooks     |
      +------------------------------+------------------------------+
                                     |
                                     v
      +-------------------------------------------------------------+
      |  3. Human Review & Approval                                 |
      |     - Senior SRE reviews playbook in data/runbooks/drafts/  |
      |     - Runs: chatops approve <draft_filename>                |
      +------------------------------+------------------------------+
                                     |
                                     v
      +-------------------------------------------------------------+
      |  4. Promotion & Instant Indexing                            |
      |     - Moves file from drafts/ to data/runbooks/             |
      |     - Chunks text into 400-token sections with 50-overlap   |
      |     - Computes deterministic SHA-256 chunk IDs              |
      |     - Indexes chunks into Chroma internal_runbooks          |
      |     - Playbook is immediately searchable in <10ms!          |
      +-------------------------------------------------------------+
```

---

## 9. Empirical Results & Proof Points (The Brag Sheet)

We ran an extensive evaluation suite consisting of **48 baseline matrix evaluations** (12 scenarios × 2 ablations × 2 trials) and **20 cross-service variant evaluations**:

### 1. Accuracy & Diagnosis Quality
- **Evidence-First Agent**: **66.7%** exact failure-type match [95% Wilson CI: 46.7% – 82.0%].
- **Baseline LLM-Only Agent**: **20.8%** exact match.
- **Lift**: **3.2× improvement** purely by forcing the agent to collect telemetry before consulting runbooks!
- **Fix Quality Score**: **80.6%** (Evidence-First) vs **49.4%** (LLM-Only).
- **Runbook Citation Rate**: **100.0%** trace-verified citations (vs 0% LLM-Only).
- **Canonical Coverage**: **100% (14/14)** across both trials on 7 out of 10 failure types (`oom`, `baddeploy`, `badenv`, `crashloop`, `depfail`, `diskfull`, `healthfail`).

### 2. Generalization & Memory Performance
- **Cross-Service Variant Benchmark**: **55.0%** accuracy across 20 unseen parameterized variants.
- **Combined Live Evaluation Matrix**: **61.4% (27/44)** overall accuracy across all live chaos runs.
- **Task T9 Hold-Out Incident Memory**: **3/3 (100%) accuracy, 0% wrong-type rate, 0 ground-truth leaks** on unseen run `r6`.
- **LogHub Drain3 Mining**: Parsed 2,000 public HDFS logs into 48 templates with **97.6% compression** in 0.008 seconds.

### 3. Latency & Cost
- **Average Diagnosis Latency**: ~20.46 seconds (including multiple HTTP round-trips to Bedrock and live container inspects).
- **Average Cost per Incident**: **$0.0129** (less than 1.5 cents per incident investigation!).

---

## 10. End-to-End Walkthrough of a Real Incident

Here is what happens second-by-second during a real incident:

1. **Failure Occurs (T = 0s)**:  
   A sudden burst of transactions causes `payment-service` to allocate memory beyond its 64MB cgroup limit. The Linux kernel OOM-killer sends `SIGKILL` (exit code 137). Docker restarts the container.
2. **Alert Raised in Slack (T = 5s)**:  
   An on-call engineer mentions the bot:  
   `@chatops-sre why is payment-service failing?`
3. **Immediate Acknowledgment (T = 6s)**:  
   The bot posts: `🔍 Investigating… please wait.`
4. **Autonomous Evidence Gathering (T = 7s – 22s)**:  
   - Agent calls `get_pod_status("payment-service")`: sees `restart_count: 1`, `exit_code: 137`, `memory_limit: 64MB`.
   - Agent calls `get_logs("payment-service")`: discovers `Memory leak: allocated 10 MB, total leaked: 10 MB`.
   - Agent calls `get_metrics("payment-service")`: sees memory peaked at 72.6MB before container death.
   - Agent calls `what_changed("payment-service")`: sees container died and restarted with exit code 137.
5. **Runbook Consultation (T = 23s – 25s)**:  
   - Evidence gate unlocks.
   - Agent queries `search_runbooks("payment-service container killed exit code 137 memory exceeded")`.
   - Chroma retrieves `OOMKilled: Payment Service Memory Limit Exceeded` (score 0.74).
6. **Diagnosis Card Posted (T = 26s)**:  
   The Slack message transforms into a rich Block Kit card with 80% confidence, citing exit code 137, quoting the runbook, and proposing:  
   `Action: set_memory_limit on payment-service to 256MB (Risk: MEDIUM)`.
7. **Thread Follow-Up (T = 40s)**:  
   Engineer asks in thread: *"What command did you use to verify that exit code?"*  
   Bot remembers context via LangGraph checkpointer and replies: *"I inspected container lifecycle via get_pod_status, which returned exit_code 137 and oom_killed true."*
8. **One-Click Human Approval (T = 55s)**:  
   The authorized engineer clicks **`[ ✅ Approve & Apply ]`**.
   - System checks `APPROVER_SLACK_IDS` (authorized).
   - Validates single-use token and invalidates it immediately.
   - Executes `docker update --memory 256m payment-service`.
   - Container memory expands from 64MB to 256MB live.
   - Audit trail `audit_3ce09e2a9426` logged.
9. **Post-Fix Verification (T = 85s)**:  
   After 30 seconds, background watcher evaluates health:  
   Posts in thread: `✅ Post-Fix Verification: Improved on payment-service — service stable, no restarts.`
10. **Incident Closed**:  
    Total MTTR: **under 90 seconds** from alert to verified resolution!
