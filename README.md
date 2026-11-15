# ChatOps SRE Agent 🩺🤖

> **An autonomous, Evidence-First AI Site Reliability Engineer that investigates, diagnoses, and remediates microservice outages live via Slack and CLI.**

[![CI Suite](https://img.shields.io/badge/pytest-48%20passed-brightgreen.svg)]()
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Architecture](https://img.shields.io/badge/architecture-Evidence--First%20%7C%20MCP-purple.svg)]()

---

## ⚡️ Key Highlights

- **Evidence-First Code Gate**: Strictly interrogates runtime container states, exit codes, error logs, and Prometheus metrics **before** consulting runbooks, eliminating confirmation bias and hallucinated metrics (achieving **66.7% vs 20.8% accuracy** over LLM-only baselines — a **3.2× lift**).
- **Dual-Collection Vector Store**:
  - `internal_runbooks`: 10 company standard operating procedures (boosted +0.03).
  - `external_knowledge`: 105 public real-world incident postmortems across 430 chunks with public URL citations.
- **Novel & Surprise Failure Handling**: Diagnoses unindexed outages (e.g. Postgres password mismatch or pool exhaustion) from raw telemetry without playbooks.
- **Human-in-the-Loop Cryptographic Safety**: Proposes non-destructive dry-runs; requires authorized Slack sign-off with single-use tokens, SHA-256 parameter tampering verification, and 30-second post-fix auto-rollback.
- **Continuous Learning Loop**: Resolves novel incidents, auto-drafts structured playbooks into quarantine, and promotes them to the active Chroma index in seconds upon human approval.
- **Multi-Turn Slack Bot**: Bidirectional Slack Socket Mode integration with rich Block Kit diagnosis cards and contextual thread memory.

---

## 🏗️ Architecture Overview

The system decouples the reasoning agent (**Person A / Brain**) from the infrastructure tools (**Person B / Body**) using the **Model Context Protocol (MCP)**:

```
                  Slack Bot / ChatOps CLI
                            |
                            v
          LangGraph ReAct Agent (Bedrock Qwen3 VL 235B)
                            |
              [ Hard Gate: evidence_gate.py ]
              /                             \
     Live Telemetry First            Dual-Collection RAG
   (K8s / Logs / Prometheus)       (Internal & External Chroma)
              |                             |
              +--------------+--------------+
                             |
                             v
              Cryptographic Remediation Engine
                 (Dry-Run & Slack Approval)
```

For the complete technical breakdown, read our comprehensive [System Explainer Guide](file:///Users/nikhi/Desktop/Chatops/chatops-agent/docs/SYSTEM_EXPLAINER.md).

---

## 🚀 Quick Start

### 1. Prerequisites & Virtual Environment
- Python 3.10+
- Docker & Docker Compose
- AWS Bedrock Credentials (or Bedrock API key)

```bash
# Clone and enter repo
cd chatops-agent

# Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-agent.txt -r requirements-infra.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
# Set AWS credentials and Slack tokens (if testing Slack bot)
```

### 3. Start the Infrastructure Stack
```bash
python infra/manage.py up
python infra/manage.py ps
```
*Starts 9 containers: `payment-service`, `order-service`, `inventory-service`, `postgres`, `prometheus`, `grafana`, `cadvisor`, `toxiproxy`, `loadgen`.*

### 4. Ingest Runbooks into Chroma Vector DB
```bash
python rag/ingest.py              # Ingests 10 internal runbooks (62 chunks)
python rag/ingest_external.py     # Ingests 105 external postmortems (430 chunks)
```

---

## 🛠️ Usage & Verification

### Diagnose an Incident via CLI
```bash
# Ask the agent to investigate an incident
python -m agent.api "why is payment-service failing?"

# Search runbooks directly (bypassing agent evidence gate)
python rag/search.py "container killed exit code 137 out of memory"
```

### Run the Interactive Slack Bot
```bash
python interfaces/slack/app.py
```
*In Slack: `@chatops-sre why is payment-service failing?`*

### Inject Chaos Failure Scenarios
```bash
# Injects an Out-of-Memory failure into payment-service
python infra/failures/run_scenario.py run oom-payment-001

# Cleanly restores the stack to healthy baseline
python infra/failures/run_scenario.py restore
```

### Automated Manual Verification Runner
We provide an all-in-one test runner covering all 11 evaluation sections:
```bash
# Run all automated tests (A through K)
python run_manual_checks.py --all-auto

# Run specific sections
python run_manual_checks.py --section H   # Remediation Safety & Auto-Rollback
python run_manual_checks.py --section I   # Continuous Learning Loop
python run_manual_checks.py --section J   # Incident Memory & LogHub Mining
```

---

## 📊 Empirical Evaluation Results

Evaluated across **48 baseline trials** and **20 cross-service variants**:

| Metric | LLM-Only Baseline | Evidence-First Agent | Improvement |
|:---|:---:|:---:|:---:|
| **Exact Failure Match** | 20.8% | **66.7%** | **+45.9% (3.2× lift)** |
| **Fix Quality Score** | 49.4% | **80.6%** | **+31.2%** |
| **Trace-Verified Citations** | 0.0% | **100.0%** | **+100.0%** |
| **Unseen Run Memory Accuracy**| N/A | **100.0% (3/3)** | **0 leaks** |
| **Average Cost / Incident** | $0.0016 | **$0.0129** | **< 1.5 cents** |
| **Average Latency** | 10.91s | **20.46s** | Deep telemetry collection |

---

## 📖 Documentation Index

- **[System Explainer Guide](file:///Users/nikhi/Desktop/Chatops/chatops-agent/docs/SYSTEM_EXPLAINER.md)**: Master explainer for presentations and explaining the architecture to peers.
- **[Manual Testing Guide](file:///Users/nikhi/Desktop/Chatops/chatops-agent/MANUAL_TESTING_GUIDE.md)**: Step-by-step checklist for all 12 manual testing sections.
- **[Viva Defense & Technical Q&A](file:///Users/nikhi/Desktop/Chatops/chatops-agent/docs/viva.md)**: 25 technical defense questions, design rationale, and honest limitations.
- **[Presentation & Demo Script](file:///Users/nikhi/Desktop/Chatops/chatops-agent/docs/demo_script.md)**: 10-minute minute-by-minute demonstration script.
- **[Agent Architecture Deep Dive](file:///Users/nikhi/Desktop/Chatops/chatops-agent/docs/agent.md)**: RAG chunking, LangGraph state machine, and multi-agent design.
- **[Infrastructure & Chaos Suite](file:///Users/nikhi/Desktop/Chatops/chatops-agent/docs/infra.md)**: Docker compose topology, Toxiproxy failure injection, and Prometheus metrics.

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](file:///Users/nikhi/Desktop/Chatops/chatops-agent/LICENSE) file for details.
