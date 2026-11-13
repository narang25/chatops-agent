# ChatOps AI SRE Agent — Master Documentation & Interview Preparation Portal

> **Portal Version:** 1.0.0  
> **Repository Root:** `/Users/nikhi/Desktop/Chatops/chatops-agent`  
> **Prepared For:** Site Reliability Engineers, Software Architects, Technical Interview Candidates  
> **Mission:** Transform this codebase into an authoritative, beginner-to-advanced learning resource and interview preparation guide.

---

## 1. Project Overview & Elevator Summary

The **ChatOps AI SRE Agent** is an autonomous diagnostic and remediation-recommendation platform built to resolve microservice operational outages. When an alert fires or a container crashes, an engineer queries the agent via CLI or Slack:
> *"Why did payment-service fail?"*

Instead of acting as a naive text chatbot that merely summarizes a document, the agent executes an **Evidence-First Protocol** over the **Model Context Protocol (MCP)**:
1. It inspects live container runtime states (`get_pod_status`), error logs (`get_logs`), and Prometheus metrics (`get_metrics`) first.
2. It derives the root-cause symptom query from empirical telemetry signatures rather than subjective user complaints.
3. It queries a dual-collection vector database in Chroma DB (internal company playbooks vs 50 real-world public incident postmortems) using dense 384-dimensional embeddings (`all-MiniLM-L6-v2`).
4. It enforces a strict **Zero-Direct-Mutation Safety Boundary**: it possesses no tools to mutate production infrastructure; it outputs non-destructive dry-run remediation proposals (`propose_remediation`) that require explicit human approval via single-use tokens.
5. In empirical benchmarks across 6 ablation configurations, Evidence-First improved diagnostic accuracy from **60.0% to 90.0%** while resisting indirect prompt injection in application logs.

---

## 2. Master Documentation Directory Links

This documentation suite is organized into 10 structured, deeply cross-referenced guides:

| File | Document Title & Scope | Primary Topics Covered |
|:---|:---|:---|
| **[`01-PROJECT-ARCHITECTURE.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/01-PROJECT-ARCHITECTURE.md)** | **System Architecture & Design Specification** | System purpose, dual explanations (beginner vs senior engineer), component decomposition, Mermaid architecture diagrams, trade-offs, and lifecycles. |
| **[`02-FILE-BY-FILE-EXPLANATION.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/02-FILE-BY-FILE-EXPLANATION.md)** | **Comprehensive File-by-File Technical Guide** | Exhaustive analysis of every meaningful file: purpose, imports, functions, classes, async flows, error handling, underlying concepts, and interview Q&A. |
| **[`03-EXECUTION-AND-DATA-FLOW.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/03-EXECUTION-AND-DATA-FLOW.md)** | **Complete Execution & Data Flow Walkthrough** | 7 end-to-end execution flows with sequence diagrams: CLI OOM triage, Slack bot Socket Mode, novel failure fallback, learning loop, and chaos failure injection. |
| **[`04-TECHNOLOGY-DEEP-DIVE.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/04-TECHNOLOGY-DEEP-DIVE.md)** | **Technology Deep-Dive & Fundamentals** | In-depth theory and code usage for Python asyncio/GIL, LangGraph, Bedrock Converse API, Ollama, MCP, Chroma DB, PromQL, Docker cgroups, and FastAPI. |
| **[`05-INTERVIEW-QUESTION-BANK.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/05-INTERVIEW-QUESTION-BANK.md)** | **Technical Interview Question Bank (12 Categories)** | 30 realistic, challenging interview questions with difficulty tiers, interviewer testing goals, strong technical answers, simple explanations, and follow-ups. |
| **[`06-CODE-REVIEW-AND-IMPROVEMENTS.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/06-CODE-REVIEW-AND-IMPROVEMENTS.md)** | **Code Quality, Security & Architecture Review** | Critical review identifying real production bugs: unpooled database connections, in-memory checkpointer limits, regex parsing flaws, and worker thread leakage. |
| **[`07-HANDS-ON-PRACTICE.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/07-HANDS-ON-PRACTICE.md)** | **Practical Hands-On Practice Guide** | 6 progressive coding challenges from adding Prometheus metrics to building disk-full failure scenarios and rebuilding the RAG engine from scratch. |
| **[`08-LEARNING-ROADMAP.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/08-LEARNING-ROADMAP.md)** | **Structured Learning Roadmap & 14-Day Plan** | Prerequisite-driven sequencing across 6 mastery levels and an accelerated daily study plan with concrete milestones. |
| **[`09-PROJECT-INTERVIEW-PITCH.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/09-PROJECT-INTERVIEW-PITCH.md)** | **Interview Pitch & Technical Defense Guide** | 30s elevator pitch, 60s overview, 3-minute architectural walkthrough, feature defenses, and authentic guidance on discussing AI-assisted development. |
| **[`99-ALL-TECHNOLOGIES-AND-LANGUAGES.md`](file:///Users/nikhi/Desktop/Chatops/docs/interview-prep/99-ALL-TECHNOLOGIES-AND-LANGUAGES.md)** | **Complete Technology, Language & Dependency Inventory** | Exhaustive catalog of every language, framework, database, tool, and protocol with versions, code locations, learning priorities, and quick-copy list. |

---

## 3. High-Level Codebase Map

```
chatops-agent/
├── agent/                         # Person A Domain: Agent Brain & Orchestration
│   ├── config.yaml                # Active LLM provider & hyperparameters
│   ├── llm.py                     # Bedrock/Ollama connector & reasoning token cleaner
│   ├── agent.py                   # LangGraph ReAct compiled graph & tool bindings
│   ├── api.py                     # Public API gateway (ask) with MemorySaver
│   ├── stub_tools.py              # In-process synthetic test telemetry
│   ├── learning/
│   │   └── draft_runbook.py       # Continuous learning loop (draft & approve)
│   ├── multi/
│   │   └── sub_agents.py          # Parallel multi-agent specialist architecture
│   ├── eval/                      # Benchmark evaluation harness & adversarial suite
│   │   ├── scenarios.py           # 10 ground-truth failure scenarios
│   │   ├── benchmark.py           # 6-ablation benchmark execution engine
│   │   ├── adversarial.py         # Prompt-injection & hallucination tests
│   │   ├── learning_curve.py      # Learning loop before/after evaluation
│   │   └── generate_charts.py     # Pure-Python SVG chart generator
│   └── scripts/                   # Model smoke testing and comparison scripts
│
├── rag/                           # Person A Domain: Knowledge Retrieval Engine
│   ├── ingest.py                  # Internal runbook chunking & Chroma upsert
│   ├── ingest_external.py         # 50 external incident postmortems ingestion
│   ├── chain.py                   # Standalone RAG chain baseline
│   └── eval/                      # Retrieval hit-rate evaluation harness
│
├── mcp_servers/                   # Shared Interface: Model Context Protocol Tool Servers
│   ├── runbooks/server.py         # Person A: search_runbooks MCP server
│   ├── prometheus/server.py       # Person B: get_metrics PromQL MCP server
│   └── kubernetes/server.py       # Person B: get_pod_status, get_logs, get_events MCP server
│       └── backends/              # Pluggable Docker vs Kubernetes runtime backends
│
├── sample_apps/                   # Person B Domain: Target Microservices Under Test
│   ├── payment-service/           # FastAPI service on :8001 (/pay, /leak, /burn)
│   ├── order-service/             # FastAPI service on :8002 (calls payment-service)
│   └── inventory-service/         # FastAPI service on :8003 (stock checks)
│
├── infra/                         # Person B Domain: Infrastructure, Chaos & Observability
│   ├── docker-compose.yml         # 8-container stack deployment
│   ├── manage.py                  # Cross-platform CLI management wrapper
│   ├── loadgen/                   # Steady background HTTP traffic generator
│   ├── failures/                  # Automated failure injection scripts (oom, bad_env, etc.)
│   ├── prometheus/                # Scrape configs & alert rules
│   ├── grafana/                   # Pre-provisioned dashboards & datasources
│   ├── k8s/                       # Kubernetes deployment manifests
│   └── tests/test_tools.py        # Automated MCP contract test harness
│
├── interfaces/                    # Presentation Layer
│   ├── cli/chatops.py             # Typer/Rich command-line interface
│   └── slack/app.py               # Slack Bolt Socket Mode interactive bot
│
├── data/                          # Ground Truth & Knowledge Datasets
│   ├── runbooks/                  # 10 internal Markdown SRE playbooks
│   │   └── drafts/                # Quarantined draft runbooks awaiting approval
│   ├── external/                  # 50 real-world public incident postmortems
│   └── incident_logs/             # Captured .jsonl logs & .meta.json ground truth
│
└── contracts/                     # Team API Contracts (Shared Interface Specs)
    ├── mcp_tools.md               # Tool signatures and return schemas
    ├── failure_types.md           # 10 canonical failure type identifiers
    ├── logs.md                    # Single-line JSON log schema
    └── metrics.md                 # Prometheus metric names and labels
```

---

## 4. Top 15 Concepts You Must Understand to Defend This Project

1. **Evidence-First Protocol:** Why querying live telemetry *before* searching vector playbooks eliminates confirmation bias and raised accuracy from 60% to 90%.
2. **Model Context Protocol (MCP):** How standardized JSON-RPC 2.0 schemas over stdio decouple the agent brain from monitoring tools.
3. **LangGraph ReAct Cyclic Graphs:** How `create_react_agent` executes cyclic reasoning loops, routes tool calls, and handles message state.
4. **State Checkpointing (`MemorySaver`):** How thread IDs preserve conversation history across turns in Slack threads.
5. **Dense Vector Embeddings & HNSW:** How `all-MiniLM-L6-v2` produces 384-dimensional dense vectors indexed via HNSW graphs in Chroma DB.
6. **Semantic Section Chunking:** Why parsing by `## Section Title` headers with 100-character overlaps preserves operational context better than naive token windowing.
7. **Dual-Collection Vector Isolation:** Why internal corporate playbooks are segregated from public incident postmortems with a $+0.03$ internal priority bonus.
8. **Similarity Thresholding & Unknown Fallback:** Why scores below $0.60$ trigger `no_confident_match: true` and an explicit `unknown` failure type instead of hallucinating.
9. **Zero-Direct-Mutation Safety Boundary:** Why autonomous infrastructure mutation is an anti-pattern; how dry-run proposals enforce human approval.
10. **Continuous Learning Loop Quarantine:** Why `status: draft` in frontmatter quarantines unreviewed runbooks from live retrieval until explicitly approved.
11. **Indirect Prompt Injection Sandboxing:** Why telemetry must be treated as untrusted data, and how structural tool omission protects infrastructure.
12. **Linux Kernel cgroups & Signal 9 Arithmetic:** How setting memory limits triggers the Linux OOM killer and produces exit code 137 ($128 + 9$).
13. **PromQL Rate Calculations:** How `rate()` calculates per-second request and error rates over rolling windows while handling counter resets.
14. **Slack 3-Second ACK Boundary:** How asynchronous background threads prevent Slack from dropping WebSocket connections during multi-second LLM reasoning.
15. **Multi-Agent Scale Trade-Offs:** Why parallel specialist sub-agents (`LogAgent`, `MetricsAgent`, `EventsAgent`) cost 2.4x more without improving accuracy at small microservice scale.

---

## 5. Most Important Files to Study First

If you have limited time, study these five core files in order:
1. **[`agent/agent.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/agent.py):** The heart of the agent. Study the `AGENT_SYSTEM_PROMPT`, tool registration, and LangGraph compilation.
2. **[`agent/api.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/api.py):** The public interface. Study how `ask()` wraps graph execution, memory checkpoints, and metadata parsing.
3. **[`rag/ingest.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest.py):** The knowledge foundation. Study frontmatter extraction, section chunking, and deterministic chunk IDs.
4. **[`mcp_servers/runbooks/server.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/mcp_servers/runbooks/server.py):** The retrieval gateway. Study dual-collection ranking, internal bonuses, and the 0.60 confidence threshold.
5. **[`interfaces/slack/app.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/interfaces/slack/app.py):** The real-world interface. Study the decoupled thread architecture that solves Slack's 3-second ACK rule.

---

## 6. Recommended Reading Order

```
[ Step 1: Broad Understanding ]
   00-START-HERE.md               (This master portal)
   01-PROJECT-ARCHITECTURE.md     (System design, diagrams & trade-offs)

[ Step 2: Implementation Mechanics ]
   03-EXECUTION-AND-DATA-FLOW.md  (Trace the 7 end-to-end execution flows)
   02-FILE-BY-FILE-EXPLANATION.md (Exhaustive analysis of every source file)

[ Step 3: Technology Deep Dive ]
   04-TECHNOLOGY-DEEP-DIVE.md     (Underlying theory: Python, LangGraph, PromQL, Docker)
   99-ALL-TECHNOLOGIES-AND-LANGUAGES.md (Complete inventory & prerequisites)

[ Step 4: Critical Thinking & Hands-On Mastery ]
   06-CODE-REVIEW-AND-IMPROVEMENTS.md (Real-world production bugs & refactorings)
   07-HANDS-ON-PRACTICE.md        (6 hands-on coding and rebuild exercises)

[ Step 5: Interview Preparation & Verbal Defense ]
   08-LEARNING-ROADMAP.md         (14-day study plan & mastery hierarchy)
   09-PROJECT-INTERVIEW-PITCH.md  (30s, 60s, and 3-minute verbal walkthroughs)
   05-INTERVIEW-QUESTION-BANK.md  (30 tough interview questions across 12 categories)
```

---

## 7. Study & Verification Checklist

- [ ] Can you whiteboard the LangGraph cyclic ReAct loop from memory?
- [ ] Can you explain why RAG-First achieves only 60% accuracy while Evidence-First achieves 90%?
- [ ] Can you explain why Linux containers exit with code 137 when killed by the OOM killer?
- [ ] Can you trace how an SRE's question in Slack reaches Bedrock and updates the Slack message in-place?
- [ ] Can you explain how deterministic chunk IDs (`{filename}::{section}::{idx}`) guarantee idempotent Chroma upserts?
- [ ] Can you defend why you used local `all-MiniLM-L6-v2` embeddings instead of cloud embeddings?
- [ ] Can you explain the trade-offs of the parallel multi-agent architecture and why you retained monolithic ReAct as default?
- [ ] Can you explain how the Zero-Direct-Mutation boundary protects production infrastructure from prompt injection attacks?
- [ ] Can you deliver the 60-second interview pitch confidently without reading notes?

---

## 8. Known Coverage & Environment Limitations

1. **Hardware / OS Context:** Developed and tested on macOS (Apple Silicon / Darwin) and Linux containers (`Alpine Linux` in Docker Desktop). Kubernetes manifests (`infra/k8s/`) are designed for local Minikube or standard clusters.
2. **Cloud Model Quotas:** Foundation model inference via Amazon Bedrock Converse API (`qwen.qwen3-vl-235b-a22b`) requires active AWS IAM credentials or bearer tokens in `.env.agent`. In offline or sandbox environments without network access, the system falls back seamlessly to `--stub` mode or local Ollama.
3. **Database Connection Pooling:** As documented in `06-CODE-REVIEW-AND-IMPROVEMENTS.md`, sample microservices currently instantiate unpooled `psycopg2.connect()` calls per request. For high-concurrency production deployments ($>100$ req/s), a connection pooler like `pgBouncer` or `ThreadedConnectionPool` must be deployed.
