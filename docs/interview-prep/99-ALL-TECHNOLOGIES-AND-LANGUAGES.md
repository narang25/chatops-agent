# ChatOps AI SRE Agent — Complete Technology, Language & Dependency Inventory

> **Document ID:** `99-ALL-TECHNOLOGIES-AND-LANGUAGES`  
> **Target Audience:** Technical Interviewers, Candidates, Software Engineers  
> **Scope:** Exhaustive catalog of every programming language, library, framework, database, runtime, tool, protocol, and architectural concept observed in the repository.

---

## 1. Programming Languages

### 1.1 Python
- **Exact Version:** `>= 3.11` (Runtime environment observed: `Python 3.14.0`)
- **Category:** Core Programming Language
- **Where Used:** Throughout `agent/`, `rag/`, `mcp_servers/`, `sample_apps/`, `infra/failures/`, `interfaces/`.
- **Why Used:** Industry standard for AI agent orchestration, machine learning embeddings, and asynchronous systems scripting.
- **Dependency Type:** Built-in Platform Runtime.
- **Learning Importance:** **Must Know (Foundational)**.
- **Prerequisites:** Object-oriented programming, data structures, exception handling.

### 1.2 Bash / POSIX Shell
- **Exact Version:** Bash 3.2+ / POSIX sh
- **Category:** Shell Scripting & Automation
- **Where Used:** [`setup_repo.sh`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/setup_repo.sh), [`infra/failures/restore.sh`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/failures/restore.sh).
- **Why Used:** Initial repository scaffolding, directory skeleton creation, container teardown scripts.
- **Dependency Type:** Operating System Utility.
- **Learning Importance:** **Should Know**.
- **Prerequisites:** Unix command-line basics, environment variables, I/O redirection.

### 1.3 YAML
- **Exact Version:** YAML 1.2
- **Category:** Configuration & Declarative Specifications
- **Where Used:** [`agent/config.yaml`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/config.yaml), [`infra/prometheus/prometheus.yml`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/prometheus/prometheus.yml), [`infra/k8s/*.yaml`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/k8s/00-namespace.yaml), [`rag/eval/questions.yaml`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/eval/questions.yaml).
- **Why Used:** Human-readable declarative configuration for LLM settings, Kubernetes manifests, Prometheus scrape configs, and evaluation benchmarks.
- **Dependency Type:** Configuration Format.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** Key-value mappings, lists, scalar data types.

### 1.4 SQL (Structured Query Language)
- **Exact Version:** ANSI SQL / PostgreSQL 15 Dialect
- **Category:** Relational Database Query Language
- **Where Used:** Embedded in [`sample_apps/payment-service/app/main.py#L112-L120`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/main.py#L112-L120) and `inventory-service/app/main.py`.
- **Why Used:** Relational table creation (`CREATE TABLE IF NOT EXISTS payments`) and transactional record insertion (`INSERT INTO payments`).
- **Dependency Type:** Embedded Query Language.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** Relational data modeling, primary keys, transactions.

### 1.5 PromQL (Prometheus Query Language)
- **Exact Version:** Prometheus 2.x+ Dialect
- **Category:** Time-Series Metric Query Language
- **Where Used:** [`mcp_servers/prometheus/server.py#L36-L54`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/prometheus/server.py#L36-L54), [`infra/grafana/provisioning/dashboards/chatops-dashboard.json`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/grafana/provisioning/dashboards/chatops-dashboard.json).
- **Why Used:** Querying instantaneous metric values, calculating rate of increase over rolling windows (`rate()`), and aggregating container memory and CPU telemetry.
- **Dependency Type:** Domain-Specific Query Language.
- **Learning Importance:** **Must Know (SRE Core)**.
- **Prerequisites:** Instant vectors, range vectors, aggregation operators (`sum by`).

### 1.6 Markdown & YAML Frontmatter
- **Exact Version:** CommonMark with YAML Frontmatter
- **Category:** Structured Document Format
- **Where Used:** [`data/runbooks/*.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/data/runbooks/out_of_memory-payment.md), [`data/external/*.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/data/external/k8s-coredns-crashloop.md), [`contracts/*.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/contracts/mcp_tools.md).
- **Why Used:** Standardized format for operational runbooks combining structured metadata with human-readable diagnostic sections (`## Symptoms`, `## Fix`).
- **Dependency Type:** Documentation & Data Format.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** Markdown syntax, frontmatter metadata boundaries (`---`).

### 1.7 JSON Lines (JSONL)
- **Exact Version:** JSON Lines Standard
- **Category:** Structured Log Format
- **Where Used:** Microservice stdout logs, [`data/incident_logs/*.jsonl`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/data/incident_logs/oom-payment-001.jsonl), [`contracts/logs.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/contracts/logs.md).
- **Why Used:** High-performance, streamable structured logging allowing one valid JSON object per line.
- **Dependency Type:** Log Ingestion Format.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** JSON serialization, streaming I/O.

---

## 2. Frontend & User Interface Technologies

### 2.1 Typer
- **Exact Version:** `typer` (latest from `requirements-agent.txt`)
- **Category:** CLI Interface Framework
- **Where Used:** [`interfaces/cli/chatops.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/interfaces/cli/chatops.py).
- **Why Used:** Building modern command-line tools based on Python 3 type hints with automatic help generation and subcommands.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Should Know**.
- **Prerequisites:** Python type hints, CLI argument parsing.

### 2.2 Rich
- **Exact Version:** `rich` (from `requirements-agent.txt`)
- **Category:** Terminal Styling & Visualization
- **Where Used:** [`interfaces/cli/chatops.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/interfaces/cli/chatops.py).
- **Why Used:** Renders colored panels, formatted Markdown, tables, and animated loading spinners (`Status`) during LLM reasoning.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Should Know**.
- **Prerequisites:** ANSI terminal color codes, layout grids.

### 2.3 Slack Block Kit
- **Exact Version:** Block Kit JSON Schema (Slack Platform)
- **Category:** Declarative Messaging UI
- **Where Used:** [`interfaces/slack/app.py#L99-L174`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/interfaces/slack/app.py#L99-L174).
- **Why Used:** Formats rich, interactive diagnostic cards in Slack channels with emojis, dividers, and thread hints.
- **Dependency Type:** Cloud Platform UI Specification.
- **Learning Importance:** **Should Know**.
- **Prerequisites:** JSON layout blocks, Slack message architecture.

### 2.4 Scalable Vector Graphics (SVG)
- **Exact Version:** SVG 1.1 Specification
- **Category:** Vector Graphics Representation
- **Where Used:** [`agent/eval/generate_charts.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/eval/generate_charts.py).
- **Why Used:** Generating resolution-independent benchmark charts (`accuracy_by_ablation.svg`) using pure Python without external rendering dependencies.
- **Dependency Type:** Web Standard.
- **Learning Importance:** **Nice to Know**.
- **Prerequisites:** XML coordinate systems, vector shapes.

---

## 3. Backend Technologies, Frameworks & Protocols

### 3.1 LangGraph
- **Exact Version:** `langgraph` (from `requirements-agent.txt`)
- **Category:** Agent State Machine Framework
- **Where Used:** [`agent/agent.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/agent.py), [`agent/api.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/api.py), [`agent/multi/sub_agents.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/multi/sub_agents.py).
- **Why Used:** Orchestrates cyclic ReAct agent execution, tool-call routing, and thread-level state checkpointing via `MemorySaver`.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Must Know (Core Brain)**.
- **Prerequisites:** Directed graphs, state management, message passing.

### 3.2 LangChain Core & AWS / Ollama Adapters
- **Exact Version:** `langchain`, `langchain-core`, `langchain-aws`, `langchain-ollama`
- **Category:** Foundation Model Integration Framework
- **Where Used:** [`agent/llm.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/llm.py), [`rag/chain.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/chain.py).
- **Why Used:** Provides standardized ChatModel abstractions (`ChatBedrockConverse`, `ChatOllama`), message types (`HumanMessage`, `AIMessage`, `ToolMessage`), and `@tool` wrappers.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** LLM prompt formatting, tokenization basics.

### 3.3 Model Context Protocol (MCP)
- **Exact Version:** `mcp >= 2.0` (FastMCP / MCPServer API)
- **Category:** Standardized Agent-Tool Protocol
- **Where Used:** [`mcp_servers/runbooks/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/runbooks/server.py), [`mcp_servers/prometheus/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/prometheus/server.py), [`mcp_servers/kubernetes/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/kubernetes/server.py).
- **Why Used:** Defines formal JSON-RPC 2.0 tool interfaces between the agent and infrastructure tools.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Must Know (Architecture Key)**.
- **Prerequisites:** JSON-RPC 2.0, standard I/O pipes.

### 3.4 FastAPI & Uvicorn
- **Exact Version:** `fastapi`, `uvicorn` (from `requirements-infra.txt`)
- **Category:** ASGI Web Framework & Web Server
- **Where Used:** [`sample_apps/payment-service/app/main.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/main.py), `order-service`, `inventory-service`.
- **Why Used:** Powers the target microservices; handles HTTP routing, Pydantic data validation, and Prometheus metrics exposition.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** ASGI architecture, asynchronous request handling.

### 3.5 Slack Bolt for Python
- **Exact Version:** `slack-bolt >= 1.18.0`, `slack-sdk >= 3.27.0`
- **Category:** ChatOps Bot Framework
- **Where Used:** [`interfaces/slack/app.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/interfaces/slack/app.py).
- **Why Used:** Handles Slack events (`app_mention`) and slash commands (`/chatops`) over WebSockets in Socket Mode without inbound webhooks.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Should Know**.
- **Prerequisites:** WebSocket connections, event subscriptions.

---

## 4. Databases, Vector Stores & ORMs

### 4.1 Chroma DB
- **Exact Version:** `chromadb` (from `requirements-agent.txt`)
- **Category:** Embedded Vector Database
- **Where Used:** [`rag/ingest.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest.py), [`rag/ingest_external.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest_external.py), [`mcp_servers/runbooks/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/runbooks/server.py).
- **Why Used:** Persists dense vector embeddings, indexes them via HNSW graphs, and executes sub-millisecond approximate nearest neighbor semantic searches.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Must Know (RAG Core)**.
- **Prerequisites:** Vector space models, distance metrics (L2, Cosine).

### 4.2 SQLite 3
- **Exact Version:** SQLite 3.x (Embedded inside Chroma DB)
- **Category:** Embedded Relational Storage
- **Where Used:** Internal storage for `chroma_db/chroma.sqlite3`.
- **Why Used:** Stores document metadata, chunk text, and collection schemas backing Chroma vector indices.
- **Dependency Type:** Transitive Dependency / Built-in Engine.
- **Learning Importance:** **Nice to Know**.
- **Prerequisites:** Embedded databases, single-file storage.

### 4.3 PostgreSQL 15
- **Exact Version:** PostgreSQL 15.x (`postgres:15-alpine`)
- **Category:** Relational ACID Database
- **Where Used:** Containerized database in `infra/docker-compose.yml`, queried by `payment-service`, `order-service`, `inventory-service`.
- **Why Used:** Persists transactional order and payment data; provides realistic database latency and timeout failure scenarios.
- **Dependency Type:** Infrastructure Component.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** Relational data modeling, connection management.

### 4.4 psycopg2-binary
- **Exact Version:** `psycopg2-binary` (from `requirements-infra.txt`)
- **Category:** PostgreSQL Database Driver
- **Where Used:** [`sample_apps/*/app/main.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/main.py).
- **Why Used:** Low-level C-based PostgreSQL driver executing SQL queries against the database container.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Should Know**.
- **Prerequisites:** Database cursor management, connection parameters.

---

## 5. Machine Learning & Embedding Models

### 5.1 `sentence-transformers` & `all-MiniLM-L6-v2`
- **Exact Version:** `sentence-transformers` (from `requirements-agent.txt`), model `all-MiniLM-L6-v2`
- **Category:** Dense Embedding Model
- **Where Used:** [`rag/ingest.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest.py), [`rag/ingest_external.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest_external.py).
- **Why Used:** Encodes text into 384-dimensional dense vectors on CPU in $<5$ ms per query with zero cloud API costs.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** Transformer encoders, BERT architecture, vector normalization.

### 5.2 Qwen3 VL 235B (`qwen.qwen3-vl-235b-a22b`)
- **Exact Version:** AWS Bedrock Foundation Model Endpoint
- **Category:** Large Language Model (Foundation Model)
- **Where Used:** Primary reasoning model in `agent/config.yaml`.
- **Why Used:** Selected for high tool-calling precision, structured output adherence, and low hallucination rates.
- **Dependency Type:** Managed Cloud Service.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** Mixture-of-experts (MoE) architectures, tool binding.

### 5.3 Mistral Large 3 (`mistral.mistral-large-3-675b-instruct`)
- **Exact Version:** AWS Bedrock Foundation Model Endpoint
- **Category:** Large Language Model (Evaluation Alternative)
- **Where Used:** Evaluated in `agent/eval/benchmark.py` and `agent/scripts/compare_models.py`.
- **Why Used:** Fast inference (1.03s latency) and zero reasoning token leakage.
- **Dependency Type:** Managed Cloud Service.
- **Learning Importance:** **Should Know**.

### 5.4 Llama 3.2 1B (`llama3.2:1b`)
- **Exact Version:** Ollama Local Model
- **Category:** Local Small Language Model
- **Where Used:** Fallback provider in `agent/config.yaml`.
- **Why Used:** Allows complete agent execution and testing without AWS credentials or internet access.
- **Dependency Type:** Local Inference Model.
- **Learning Importance:** **Should Know**.

---

## 6. Observability, Metrics & System Libraries

### 6.1 `prometheus_client`
- **Exact Version:** `prometheus-client` (from `requirements-infra.txt`)
- **Category:** Metrics Instrumentation Library
- **Where Used:** [`sample_apps/*/app/metrics.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/metrics.py).
- **Why Used:** Registers and increments counters, gauges, and histograms; serializes metrics into Prometheus exposition format on `/metrics`.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** Prometheus metric types (Counter, Gauge, Histogram).

### 6.2 `psutil`
- **Exact Version:** `psutil` (from `requirements-infra.txt`)
- **Category:** Cross-Platform Process & System Telemetry
- **Where Used:** [`sample_apps/*/app/main.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/main.py).
- **Why Used:** Reads real-time RSS memory of microservice processes to update the `app_memory_bytes` gauge.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Should Know**.
- **Prerequisites:** OS process memory concepts (RSS, VMS).

### 6.3 `httpx`
- **Exact Version:** `httpx` (from `requirements-infra.txt`)
- **Category:** Modern Async/Sync HTTP Client
- **Where Used:** [`mcp_servers/prometheus/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/prometheus/server.py), [`sample_apps/order-service/app/main.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/order-service/app/main.py), [`infra/loadgen/loadgen.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/loadgen/loadgen.py).
- **Why Used:** Executes non-blocking HTTP requests between microservices, queries Prometheus HTTP APIs, and generates synthetic traffic.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** HTTP methods, connection pooling, timeouts.

### 6.4 `docker` (docker-py)
- **Exact Version:** `docker` (from `requirements-infra.txt`)
- **Category:** Docker Daemon SDK
- **Where Used:** [`mcp_servers/kubernetes/backends/docker_backend.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/kubernetes/backends/docker_backend.py).
- **Why Used:** Inspects container state (`OOMKilled`, `ExitCode`, `RestartCount`), queries daemon lifecycle events, and pulls container logs.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Must Know**.
- **Prerequisites:** Docker Engine API, UNIX domain sockets (`/var/run/docker.sock`).

### 6.5 `kubernetes` (Official Python Client)
- **Exact Version:** `kubernetes` (referenced in `backends/k8s_backend.py`)
- **Category:** Kubernetes Cluster API SDK
- **Where Used:** [`mcp_servers/kubernetes/backends/k8s_backend.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/kubernetes/backends/k8s_backend.py).
- **Why Used:** Interrogates Kubernetes clusters/Minikube for Pod phases, container statuses, and cluster events.
- **Dependency Type:** Optional / Pluggable Runtime Dependency.
- **Learning Importance:** **Should Know**.
- **Prerequisites:** Kubernetes API primitives (Pods, Deployments, Namespaces).

### 6.6 `python-frontmatter` & `pyyaml`
- **Exact Version:** `python-frontmatter`, `pyyaml` (from `requirements-agent.txt`)
- **Category:** Metadata Parsing Libraries
- **Where Used:** [`rag/ingest.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest.py), [`agent/learning/draft_runbook.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/learning/draft_runbook.py), [`agent/llm.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/llm.py).
- **Why Used:** Parses YAML frontmatter headers from Markdown files and loads `config.yaml`.
- **Dependency Type:** Direct Dependency.
- **Learning Importance:** **Should Know**.

---

## 7. Cloud, DevOps, Infrastructure & Testing Tools

### 7.1 Docker & Docker Compose
- **Exact Version:** Docker Compose v2.x
- **Category:** Container Orchestration & Local Infrastructure
- **Where Used:** [`infra/docker-compose.yml`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/docker-compose.yml), service Dockerfiles.
- **Why Used:** Multi-container stack provisioning (8 containers: 3 sample apps, postgres, prometheus, grafana, cadvisor, loadgen).
- **Dependency Type:** Development & Deployment Tool.
- **Learning Importance:** **Must Know**.

### 7.2 Prometheus Server
- **Exact Version:** `prom/prometheus:latest`
- **Category:** Time-Series Monitoring Platform
- **Where Used:** Container in `docker-compose.yml`, configured via `infra/prometheus/prometheus.yml`.
- **Why Used:** Scrapes microservices every 5 seconds, calculates time series, and serves diagnostic queries to the agent.
- **Dependency Type:** Infrastructure Platform.
- **Learning Importance:** **Must Know**.

### 7.3 Grafana
- **Exact Version:** `grafana/grafana:latest`
- **Category:** Metrics Visualization Platform
- **Where Used:** Container in `docker-compose.yml`, provisioned via `infra/grafana/provisioning/`.
- **Why Used:** Provides human SREs with pre-provisioned dashboards for visual validation.
- **Dependency Type:** Infrastructure Visualization.
- **Learning Importance:** **Should Know**.

### 7.4 cAdvisor
- **Exact Version:** `gcr.io/cadvisor/cadvisor:latest`
- **Category:** Container Telemetry Scraper
- **Where Used:** Container in `docker-compose.yml` (port 8085).
- **Why Used:** Extracts kernel-level container metrics (CPU seconds, memory RSS, memory limit bytes) directly from the Linux host.
- **Dependency Type:** Infrastructure Telemetry.
- **Learning Importance:** **Must Know (SRE Core)**.

### 7.5 pytest
- **Exact Version:** `pytest >= 7.0` (from `requirements-infra.txt`)
- **Category:** Automated Testing Framework
- **Where Used:** [`infra/tests/test_tools.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/tests/test_tools.py), [`mcp_servers/*/test_server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/prometheus/test_server.py).
- **Why Used:** Executes contract verification suites, mocking container and Prometheus responses to ensure tool schema compliance.
- **Dependency Type:** Development Dependency.
- **Learning Importance:** **Must Know**.

---

## 8. Architectural Patterns & Technical Concepts

1. **Evidence-First Diagnostic Protocol:** Invariant ordering requiring live container and telemetry inspection before querying runbooks.
2. **Model Context Protocol (MCP):** Decoupled, JSON-RPC 2.0 tool execution over stdio and HTTP.
3. **ReAct (Reasoning + Acting) Cycle:** Cyclic state machine alternating between thought generation and tool execution.
4. **Dense Vector Embeddings & Semantic Search:** Mathematical text representation in 384-dimensional vector space using cosine distance.
5. **Dual-Collection Knowledge Isolation:** Segregation of internal operational playbooks from public postmortems.
6. **Zero-Direct-Mutation Safety Boundary:** Structural omission of destructive tools; remediation restricted to human-gated dry-run proposals.
7. **Continuous Human-in-the-Loop Learning Loop:** Dynamic drafting and quarantining of novel incident playbooks with atomic approval upsert.
8. **Asynchronous Concurrency (`asyncio.gather`):** Concurrent network dispatch to foundation model APIs.
9. **Linux cgroups v2 & Signal Arithmetic:** Kernel memory limits and SIGKILL (exit code 137).
10. **Indirect Prompt Injection Sandboxing:** Telemetry and external documents treated as untrusted data inputs.

---

## 9. Recommended Learning Sequence

```
1. WHAT TO LEARN FIRST (Foundations):
   - Python 3 AsyncIO & Concurrency Model (async/await, event loops, GIL)
   - Docker & Linux cgroups (exit codes, memory limits, OOM-killer)
   - Prometheus & PromQL (Counter, Gauge, rate() calculations)

2. WHAT TO LEARN SECOND (Core Agent Brain):
   - LangGraph StateGraph & ReAct Cycle (messages, tool bindings, MemorySaver)
   - Model Context Protocol (MCP JSON-RPC 2.0 tool servers)
   - Dense Vector Retrieval & Chroma DB (embeddings, chunking, thresholding)

3. WHAT TO LEARN THIRD (Integration & Safety):
   - Evidence-First Protocol (why it beats RAG-First)
   - Zero-Direct-Mutation Safety Boundary & Dry-Run Proposals
   - Indirect Prompt Injection Defense & Sandboxing

4. WHAT CAN BE LEARNED LATER / NICE TO KNOW:
   - Slack Bolt Socket Mode WebSocket mechanics
   - Pure-Python SVG generation algorithms
   - Multi-agent coordinator optimization
```

---

## COMPLETE TECHNOLOGY NAMES — QUICK COPY LIST

### Programming Languages
- Python
- Bash / Shell Scripting
- YAML
- SQL (PostgreSQL dialect)
- PromQL (Prometheus Query Language)
- Markdown with YAML Frontmatter
- JSON / JSON Lines (JSONL)

### Frontend & User Interface Technologies
- Typer
- Rich
- Slack Block Kit
- Slack Socket Mode
- Scalable Vector Graphics (SVG)

### Backend Technologies & Frameworks
- LangGraph
- LangChain Core
- LangChain AWS
- LangChain Ollama
- Model Context Protocol (MCP)
- FastAPI
- Uvicorn
- Slack Bolt for Python

### Databases, Vector Stores & Drivers
- Chroma DB
- SQLite 3
- PostgreSQL 15
- psycopg2 / psycopg2-binary

### Machine Learning & Foundation Models
- sentence-transformers (`all-MiniLM-L6-v2`)
- Qwen3 VL 235B (`qwen.qwen3-vl-235b-a22b`)
- Mistral Large 3 (`mistral.mistral-large-3-675b-instruct`)
- Llama 3.2 1B (`llama3.2:1b`)
- Amazon Bedrock Converse API
- Local Ollama Daemon

### Observability, Metrics & Telemetry
- Prometheus Server
- prometheus-client
- cAdvisor
- Grafana
- psutil
- httpx
- docker-py (Docker SDK)
- kubernetes-client (Kubernetes SDK)

### Configuration, Build & Testing Tools
- Docker & Docker Compose
- pytest
- unittest.mock
- python-dotenv
- python-frontmatter
- pyyaml
- setuptools / pip
- GNU Make

### Architectural Patterns & Concepts
- Evidence-First Protocol
- ReAct (Reasoning + Acting) Pattern
- Retrieval-Augmented Generation (RAG)
- Dual-Collection Vector Isolation
- Zero-Direct-Mutation Safety Boundary
- Human-in-the-Loop Continuous Learning Loop
- Linux cgroups v2 Memory Limit Enforcement
- Indirect Prompt Injection Sandboxing
