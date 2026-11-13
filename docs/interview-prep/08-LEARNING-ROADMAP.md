# ChatOps AI SRE Agent — Structured Learning Roadmap & 14-Day Preparation Plan

> **Document ID:** `08-LEARNING-ROADMAP`  
> **Target Audience:** Engineers transition-readying to master, defend, and rebuild the ChatOps codebase  
> **Methodology:** Prerequisite-driven sequencing across 6 mastery levels followed by an accelerated 14-day study plan.

---

## 1. Six-Level Mastery Hierarchy

```
  +-----------------------------------------------------------------+
  | Level 6: Mock Interview Defense & Live Architectural Whiteboard |
  +--------------------------------+--------------------------------+
                                   ^
  +--------------------------------+--------------------------------+
  | Level 5: Security, Performance, Scalability & Chaos Engineering |
  +--------------------------------+--------------------------------+
                                   ^
  +--------------------------------+--------------------------------+
  | Level 4: ChatOps Architecture, Evidence-First & Safety Boundary |
  +--------------------------------+--------------------------------+
                                   ^
  +--------------------------------+--------------------------------+
  | Level 3: Vector Databases, PromQL Telemetry & MCP Protocol      |
  +--------------------------------+--------------------------------+
                                   ^
  +--------------------------------+--------------------------------+
  | Level 2: Framework & Runtime Mechanics (LangGraph & FastAPI)     |
  +--------------------------------+--------------------------------+
                                   ^
  +--------------------------------+--------------------------------+
  | Level 1: Python Fundamentals, AsyncIO & Concurrency Model       |
  +-----------------------------------------------------------------+
```

---

## Level 1: Python Fundamentals, AsyncIO & Concurrency

### 1.1 Concurrency Models: `asyncio` vs `threading`
- **What You Need to Learn:** How Python's event loop executes coroutines (`async`/`await`), how the GIL affects thread scheduling during I/O vs CPU work, and when to choose `asyncio.gather()` over `threading.Thread`.
- **Why You Need to Learn It:** Interviewers will test whether you truly understand why `sub_agents.py` uses coroutines while `slack/app.py` uses daemon threads.
- **Project File:** [`agent/multi/sub_agents.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/multi/sub_agents.py) and [`interfaces/slack/app.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/interfaces/slack/app.py).
- **Depth Required:** **Deep (Architectural)**.
- **Priority:** **MUST KNOW**.
- **Self-Check Question:** *"Why does calling an LLM release the GIL in Python?"* (Answer: CPython releases the GIL during socket read/write calls in C code).

### 1.2 Resource Management & Context Managers
- **What You Need to Learn:** The Python context manager protocol (`__enter__`/`__exit__`, `@asynccontextmanager`), exception cleanup, and how FastAPI's `lifespan` manages service setup.
- **Why You Need to Learn It:** Prevents resource leaks in database connection pools and background metrics tasks.
- **Project File:** [`sample_apps/payment-service/app/main.py#L145-L165`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/main.py#L145-L165).
- **Depth Required:** Working knowledge.
- **Priority:** **SHOULD KNOW**.

---

## Level 2: Framework & Runtime Mechanics (LangGraph & FastAPI)

### 2.1 LangGraph Cyclic ReAct State Graphs
- **What You Need to Learn:** How LangGraph models cyclic reasoning loops, tool calling dispatch via `AIMessage.tool_calls`, and how `MemorySaver` saves checkpoints across turns.
- **Why You Need to Learn It:** This is the primary engine of the agent; if you cannot explain the graph transitions, you cannot defend the codebase.
- **Project File:** [`agent/agent.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/agent.py) and [`agent/api.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/api.py).
- **Depth Required:** **Expert / Deep**.
- **Priority:** **MUST KNOW**.
- **Self-Check Question:** *"What exact data is passed from the LLM node to the Tool node in LangGraph?"* (Answer: An `AIMessage` with `tool_calls` containing tool names and JSON argument dicts).

### 2.2 FastAPI Asynchronous Request Lifecycle
- **What You Need to Learn:** ASGI event loops, non-blocking HTTP endpoints, Pydantic data coercion, and Prometheus `/metrics` exposition.
- **Why You Need to Learn It:** You must understand how the sample microservices expose the telemetry that the agent investigates.
- **Project File:** [`sample_apps/payment-service/app/main.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/main.py).
- **Depth Required:** Working knowledge.
- **Priority:** **SHOULD KNOW**.

---

## Level 3: Vector Databases, PromQL Telemetry & MCP Protocol

### 3.1 Model Context Protocol (MCP) Standards
- **What You Need to Learn:** JSON-RPC 2.0 message schemas, tool registration via `@mcp.tool`, parameter introspection, and stdio transport pipes.
- **Why You Need to Learn It:** MCP is the structural contract separating the agent brain from infrastructure tools.
- **Project File:** [`mcp_servers/runbooks/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/runbooks/server.py), [`contracts/mcp_tools.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/contracts/mcp_tools.md).
- **Depth Required:** **Deep (Architectural)**.
- **Priority:** **MUST KNOW**.
- **Self-Check Question:** *"Why do MCP tools return `{'error': '...'}` instead of raising unhandled Python exceptions?"* (Answer: Returning JSON allows the LLM to read the error and self-correct instead of crashing the process).

### 3.2 Chroma DB & Dense Vector Ingestion
- **What You Need to Learn:** HNSW approximate nearest neighbor search, `all-MiniLM-L6-v2` dense embeddings, deterministic chunk ID generation, and similarity thresholding ($S \ge 0.60$).
- **Why You Need to Learn It:** RAG retrieval quality directly determines whether the agent recommends the correct remediation playbook.
- **Project File:** [`rag/ingest.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest.py) and [`mcp_servers/runbooks/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/runbooks/server.py).
- **Depth Required:** **Deep (Mathematical & Practical)**.
- **Priority:** **MUST KNOW**.

### 3.3 Prometheus TSDB & PromQL
- **What You Need to Learn:** Counters vs Gauges vs Histograms, `rate()` over rolling windows, and querying container resource metrics via cAdvisor.
- **Why You Need to Learn It:** SRE interviewers will test your ability to read and write real PromQL queries for memory and latency degradation.
- **Project File:** [`mcp_servers/prometheus/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/prometheus/server.py), [`contracts/metrics.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/contracts/metrics.md).
- **Depth Required:** Working knowledge.
- **Priority:** **MUST KNOW**.

---

## Level 4: ChatOps Architecture, Evidence-First & Safety Boundary

### 4.1 The Evidence-First Investigation Protocol
- **What You Need to Learn:** The systematic diagnostic sequence (inspect runtime status -> inspect logs & metrics -> query runbooks with observed error signatures -> propose remediation).
- **Why You Need to Learn It:** This is the core architectural innovation that improved accuracy from 60% to 90% in our benchmark.
- **Project File:** [`agent/agent.py#L39-L84`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/agent.py#L39-L84).
- **Depth Required:** **Expert**.
- **Priority:** **MUST KNOW**.

### 4.2 Safe Remediation & The Zero-Direct-Mutation Boundary
- **What You Need to Learn:** Why autonomous LLM infrastructure mutation is an anti-pattern, how dry-run proposals work, and human-in-the-loop approval gating.
- **Why You Need to Learn It:** Demonstrates production maturity and risk awareness in system architecture interviews.
- **Project File:** [`contracts/mcp_tools.md#L73-L75`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/contracts/mcp_tools.md#L73-L75), [`agent/stub_tools.py#L210-L240`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/stub_tools.py#L210-L240).
- **Depth Required:** **Deep**.
- **Priority:** **MUST KNOW**.

---

## Level 5: Security, Performance, Scalability & Chaos Engineering

### 5.1 Indirect Prompt Injection Resilience
- **What You Need to Learn:** Threat modeling around untrusted log streams, prompt sandboxing, and adversarial regression suites.
- **Project File:** [`agent/eval/adversarial.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/eval/adversarial.py).
- **Depth Required:** Working knowledge.
- **Priority:** **SHOULD KNOW**.

### 5.2 Chaos Engineering & Failure Injection
- **What You Need to Learn:** Linux kernel cgroup OOM killer dynamics (exit code 137), container state inspection, and ground-truth validation (`.meta.json`).
- **Project File:** [`infra/failures/run_scenario.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/failures/run_scenario.py), [`infra/failures/oom.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/failures/oom.py).
- **Depth Required:** Working knowledge.
- **Priority:** **MUST KNOW**.

---

## Level 6: Mock Interview Defense & Live Architectural Whiteboard

- **What You Need to Learn:** Explaining the system confidently in 30 seconds, 60 seconds, and 3 minutes.
- **Defense Strategy:** Defend trade-offs (e.g., why monolithic ReAct beat multi-agent in cost/latency at our scale; why local embeddings beat cloud embeddings).
- **Reference Document:** [`docs/interview-prep/05-INTERVIEW-QUESTION-BANK.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/05-INTERVIEW-QUESTION-BANK.md) and [`docs/viva.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/docs/viva.md).

---

## 2. Recommended 14-Day Preparation Schedule

```
Day 1-2:   Core Foundations (Python Async, LangGraph StateGraph, Bedrock Converse)
Day 3-4:   Telemetry & Monitoring (Prometheus, PromQL, Docker cgroups, cAdvisor)
Day 5-6:   Knowledge Retrieval (Chroma DB, MiniLM embeddings, chunking algorithms)
Day 7-8:   MCP Architecture & Protocol Contracts (Runbooks, Prometheus, K8s servers)
Day 9-10:  Evidence-First Protocol & Safety Boundaries (Prompt guardrails, dry-run proposals)
Day 11-12: Benchmarking & Ablations (Ablation results, Multi-Agent trade-offs, adversarial tests)
Day 13-14: Mock Interviews, Whiteboard Rehearsal & Live Code Defense
```

### Detailed Daily Milestones

- **Day 1: Agent Brain & LLM Connection**
  - Read [`agent/llm.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/llm.py) and [`agent/config.yaml`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/config.yaml).
  - Understand `clean_output()` regex filtering and `ChatBedrockConverseFallback`.
  - *Exercise:* Run `python agent/scripts/smoke_llm.py` and inspect latency and tool binding.

- **Day 2: LangGraph ReAct Cycle**
  - Study [`agent/agent.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/agent.py) and [`agent/api.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/api.py).
  - Trace how `create_react_agent` connects tools and system prompts.
  - Understand in-memory checkpointing via `MemorySaver`.

- **Day 3: Target Microservices & Structured Logging**
  - Read [`sample_apps/payment-service/app/main.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/main.py) and `logging_config.py`.
  - Understand single-line JSON logging contract (`contracts/logs.md`).
  - *Exercise:* Spin up containers with `python infra/manage.py up` and verify `/health`.

- **Day 4: Prometheus Telemetry & PromQL Queries**
  - Read [`sample_apps/payment-service/app/metrics.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/metrics.py) and [`mcp_servers/prometheus/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/prometheus/server.py).
  - Practice PromQL rate queries in browser (`http://localhost:9090`).
  - Master container memory vs cgroup limit calculations via cAdvisor.

- **Day 5: Vector Ingestion & Semantic Chunking**
  - Read [`rag/ingest.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest.py) and [`rag/ingest_external.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest_external.py).
  - Study deterministic chunk ID generation (`{filename}::{section}::{idx}`) and context enrichment headers.
  - *Exercise:* Run `python rag/ingest.py` and observe chunk counts (62 chunks).

- **Day 6: Retrieval Tuning & Dual-Collection Search**
  - Study [`mcp_servers/runbooks/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/runbooks/server.py).
  - Understand the $+0.03$ internal priority bonus and `CONFIDENCE_THRESHOLD = 0.60`.
  - *Exercise:* Run `python rag/eval/run_eval.py` and verify Hit Rate @ 1 (85.7%) and Hit Rate @ 3 (100%).

- **Day 7: Model Context Protocol (MCP) Mastery**
  - Read [`contracts/mcp_tools.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/contracts/mcp_tools.md) and all files in `mcp_servers/`.
  - Understand how `mcp_servers/kubernetes/backends/` abstracts Docker vs Kubernetes.
  - *Exercise:* Run `python -m pytest infra/tests/test_tools.py`.

- **Day 8: Chaos Engineering & Failure Injection**
  - Read [`infra/failures/run_scenario.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/failures/run_scenario.py) and `oom.py`.
  - Master exit code 137 Linux signal arithmetic ($128 + 9 = 137$).
  - *Exercise:* Inject OOM failure: `python infra/failures/run_scenario.py run oom-payment-001`.

- **Day 9: Evidence-First Protocol & Diagnostic Trace**
  - Read [`docs/interview-prep/03-EXECUTION-AND-DATA-FLOW.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/03-EXECUTION-AND-DATA-FLOW.md).
  - Trace every step of `chatops ask "payment-service is crashing"`.
  - Understand why live telemetry inspection must precede runbook queries.

- **Day 10: Safety Boundaries & Continuous Learning Loop**
  - Read [`agent/learning/draft_runbook.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/learning/draft_runbook.py).
  - Master the draft quarantine mechanism (`status: draft`).
  - *Exercise:* Run `python -m agent.eval.learning_curve --type out_of_memory`.

- **Day 11: Benchmark Results & Multi-Agent Evaluation**
  - Study [`agent/eval/results/final_benchmark_report.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/eval/results/final_benchmark_report.md).
  - Memorize key numbers: Full System (90% accuracy, 16.4s latency, $0.0075 cost) vs Multi-Agent (90% accuracy, 31.8s latency, $0.0185 cost).
  - Explain why multi-agent added overhead without accuracy gain.

- **Day 12: Security & Adversarial Defense**
  - Read [`agent/eval/adversarial.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/eval/adversarial.py).
  - Understand indirect prompt injection, prompt sandboxing, and structural tool omission.
  - *Exercise:* Run `python -m agent.eval.adversarial`.

- **Day 13: Presentation Interfaces (CLI & Slack Bot)**
  - Read [`interfaces/cli/chatops.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/interfaces/cli/chatops.py) and [`interfaces/slack/app.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/interfaces/slack/app.py).
  - Explain Slack's 3-second ACK deadline and the background thread replacement pattern.

- **Day 14: Mock Interview & Verbal Rehearsal**
  - Rehearse all 12 categories in [`docs/interview-prep/05-INTERVIEW-QUESTION-BANK.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/05-INTERVIEW-QUESTION-BANK.md).
  - Rehearse the 30s, 60s, and 3-minute pitches from [`docs/interview-prep/09-PROJECT-INTERVIEW-PITCH.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/09-PROJECT-INTERVIEW-PITCH.md).
  - Whiteboard the full system architecture diagram from memory.
