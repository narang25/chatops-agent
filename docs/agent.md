# ChatOps Agent & RAG Architecture (Person A — Weeks 1 & 2)

This document records the design decisions, implementation details, benchmarking results, and tuning parameters for the **Person A (Brain)** side of the ChatOps SRE agent.

---

## 1. Architecture Overview

### Week 1 (RAG Chain)
```
           Engineer / User (CLI / Script)
                        │
                        ▼
            RAG Chain (`rag/chain.py`)
           ┌────────────┴────────────┐
           ▼                         ▼
   LLM Connection            Vector Retriever
(`agent/llm.py` via         (`rag/ingest.py` via
  Amazon Bedrock /            Chroma DB + MiniLM)
  Ollama Fallback)                   │
           ▲                         ▼
           │                 Runbook Store
    Clean Output         (`data/runbooks/*.md`)
(Strips <think> tags)
```

### Week 2 (Tool-Calling Agent)
```
Engineer (CLI: `chatops ask "..."`)
              │
              ▼
    LangGraph ReAct Agent (`agent/agent.py`)
         │           │           │           │
         ▼           ▼           ▼           ▼
  search_runbooks  get_metrics  get_pod_   get_events
  (MCP Server /   (Person B /   status    (Person B /
   in-process)     stub)       (Person B / stub)
         │                      stub)
         ▼
  Chroma Vector DB
  (all-MiniLM-L6-v2)
         │
         ▼
  data/runbooks/*.md (10 runbooks)
```

---

## 2. LLM Connection (Task A1)

### Primary & Fallback Providers
- **Primary:** Amazon Bedrock using `ChatBedrockConverse` (`langchain-aws`).
- **Fallback:** Local Ollama using `ChatOllama` (`langchain-ollama`).
- **Swapping:** Configured in `agent/config.yaml` (`provider: bedrock | ollama`).

### Model Selection Benchmark (in `us-east-1`)
10 candidate models were evaluated across Hello generation, tool calling (`get_service_status`), and reasoning leakage:

| Model ID | Hello | Tool Call | Leak | Avg Latency | Status |
|---|---|---|---|---|---|
| `mistral.mistral-large-3-675b-instruct` | PASS | PASS | NONE | 1.03s | Fastest overall |
| `deepseek.v3.2` | PASS | PASS | NONE | 1.32s | Fast reasoning |
| `moonshotai.kimi-k2.5` | PASS | PASS | NONE | 1.40s | Accurate tool calling |
| `zai.glm-5` | PASS | PASS | NONE | 1.51s | Non-streaming |
| **`qwen.qwen3-vl-235b-a22b`** | **PASS** | **PASS** | **NONE** | **2.04s** | **Default Selected Model** |
| `qwen.qwen3-next-80b-a3b` | PASS | PASS | NONE | 2.70s | Verified alternative |

### Safety & Reasoning-Leak Prevention
- `clean_output(message)` in `agent/llm.py` drops internal reasoning blocks and strips `<think>...</think>` tokens using regex, ensuring raw chain-of-thought traces never reach end-users.
- Automatic cross-region inference fallback: If a model identifier raises `ValidationException`, `ChatBedrockConverseFallback` retries once with the `us.` prefix automatically.

---

## 3. Runbooks & Vector Store (Tasks A2 + Week 2 Day 8)

### Runbooks (`data/runbooks/`) — 10 total

**Week 1 (6 runbooks):**
1. `out_of_memory-payment.md`: Container OOMKilled, exit code 137, `/leak` endpoint memory exhaustion.
2. `bad_config-order.md`: Missing `PAYMENT_SERVICE_URL`, exit code 1, critical startup failure.
3. `health_check_failure-inventory.md`: Injected `health_fail` toggle, HTTP 500, Docker unhealthy state.
4. `db_timeout-payment.md`: PostgreSQL database timeout after 5s, pool exhaustion.
5. `dependency_failure-order.md`: Downstream payment-service connection refused, cascading 502/500 errors.
6. `cpu_saturation-any.md`: High CPU utilization, event loop lag, p95 latency spikes above 2000ms.

**Week 2 additions (4 new runbooks):**
7. `disk_full-any.md`: `[Errno 28] No space left on device` — Docker overlay2 / log accumulation.
8. `crash_loop-inventory.md`: Container restart loop (restart_count > 3), startup exception or bad dependency.
9. `network_timeout-payment.md`: Downstream network timeout on `/pay` — circuit breaker pattern.
10. `high_error_rate-order.md`: Sustained HTTP 5xx rate > 5% — bad deployment or cascade failure.

**New failure_types added to `contracts/failure_types.md`:** `crash_loop`, `network_timeout`, `high_error_rate`.

### Ingestion & Chunking Strategy
- **Chunking Algorithm:** Parses markdown by `##` headers (`Symptoms`, `Likely cause`, `How to confirm`, `Fix`, `Prevention`).
- **Length Overflow Windowing:** Sections exceeding 600 characters are sub-chunked with a 100-character overlap along sentence/newline boundaries.
- **Context Enrichment:** Prepends runbook title, target service, and section name to every chunk.
- **Embedding:** `sentence-transformers` with `all-MiniLM-L6-v2` (384 dimensions, zero cloud cost, local CPU execution).
- **Storage:** Persistent Chroma DB at `chroma_db/` — **62 total chunks** indexed in 0.61s (up from 32 in Week 1).
- **Idempotence:** Uses deterministic IDs (`<runbook>::<section>::<chunk_idx>`) to avoid duplicate chunks on re-runs.

---

## 4. RAG Chain with Citations (Task A3)

- **Module:** `rag/chain.py` (`RAGChain.run(question)`)
- **CLI Runner:** `python rag/scripts/ask.py "<question>"`
- **Strict Grounding Prompt:**
  1. Answers strictly from retrieved runbook context.
  2. If information is absent, explicitly reports insufficient context instead of hallucinating.
  3. Returns diagnosis, verification commands, recommended fix steps, and exact cited sources (title, file path, section, and similarity score).

---

## 5. Retrieval Evaluation & Tuning (Tasks A4 + Week 2)

### Week 2 Results (14 questions)
| Metric | Result | Target | Status |
|---|---|---|---|
| **Hit Rate @ Top-1** | **85.7%** (12/14) | >= 80% | **PASSED** |
| **Hit Rate @ Top-3** | **100.0%** (14/14) | >= 90% | **PASSED** |
| **Mean Reciprocal Rank (MRR)** | **0.929** | >= 0.85 | **PASSED** |

> Note: 2 misses (Q1 and Q4) are cross-service ambiguous queries where the correct runbook appears at rank #2. All are within Top-3.

### Detailed Evaluation Breakdown (14 questions)
| ID | Incident Query | Expected Runbook | Rank | Hit@1 | Hit@3 |
|---|---|---|---|---|---|
| 1 | Payment-service exit code 137 | `out_of_memory-payment.md` | #2 | X | Y |
| 2 | Memory climbing monotonically | `out_of_memory-payment.md` | #1 | Y | Y |
| 3 | Missing PAYMENT_SERVICE_URL | `bad_config-order.md` | #1 | Y | Y |
| 4 | Order container exits with code 1 | `bad_config-order.md` | #2 | X | Y |
| 5 | Inventory /health returning 500 | `health_check_failure-inventory.md` | #1 | Y | Y |
| 6 | Reset health_fail toggle | `health_check_failure-inventory.md` | #1 | Y | Y |
| 7 | DB connection timed out after 5s | `db_timeout-payment.md` | #1 | Y | Y |
| 8 | Cannot connect to postgres port 5432 | `db_timeout-payment.md` | #1 | Y | Y |
| 9 | Failed to call payment-service | `dependency_failure-order.md` | #1 | Y | Y |
| 10 | CPU usage 100% and latency spikes | `cpu_saturation-any.md` | #1 | Y | Y |
| 11 | `[Errno 28] No space left on device` | `disk_full-any.md` | #1 | Y | Y |
| 12 | inventory-service restart count 8 | `crash_loop-inventory.md` | #1 | Y | Y |
| 13 | Timeout calling fraud-check after 3s | `network_timeout-payment.md` | #1 | Y | Y |
| 14 | app_errors_total spiking with ValueError | `high_error_rate-order.md` | #1 | Y | Y |

### Tuned Parameters
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (Cosine / L2 distance).
- **Max Chunk Size:** 600 characters.
- **Chunk Overlap:** 100 characters.
- **Top-K Retrieval:** 3 chunks.
- **Similarity Threshold:** Normalized score > 0.60.

---

## 6. `search_runbooks` MCP Server (Week 2 Day 9)

- **Module:** `mcp_servers/runbooks/server.py`
- **Framework:** `mcp` v2.x — `MCPServer` (replaces `FastMCP` from v1).
- **Transport:** stdio (JSON-RPC over stdin/stdout).
- **Tool exposed:** `search_runbooks(query, top_k=3)` — shape matches `contracts/mcp_tools.md` exactly.
- **Errors:** Returns `{"error": "<message>"}` instead of raising.
- **Run:** `python -m mcp_servers.runbooks.server`

---

## 7. LangGraph Tool-Calling Agent (Week 2 Days 10-11)

- **Module:** `agent/agent.py`
- **Framework:** `langgraph` v1.2.x — `create_react_agent`.
- **Tools (4 total):**
  - `search_runbooks` — in-process call to the runbooks MCP server's retrieval function.
  - `get_metrics` — Person B's Prometheus MCP tool (stub in `agent/stub_tools.py`).
  - `get_pod_status` — Person B's container status tool (stub).
  - `get_events` — Person B's events MCP tool (stub).
- **Investigation protocol (system prompt):** Always calls tools in order: runbooks -> pod_status -> metrics -> events, then cross-references before concluding.
- **Stub mode:** `build_agent(stub=True)` uses realistic synthetic data — no Docker or Prometheus needed.
- **Public API:** `agent.ask(question, stub=True) -> {"question", "answer", "messages"}` — clean entry point for CLI and Slack.

---

## 8. `chatops ask` CLI (Week 2 Day 12)

- **Module:** `interfaces/cli/chatops.py`
- **Framework:** `typer` 0.27 + `rich` 15.
- **Commands:**
  - `chatops ask "<question>"` — full agent investigation with Rich panel output.
  - `chatops search "<query>"` — direct runbook search, no LLM.
- **Flags:** `--stub/--no-stub`, `--model`, `--top-k`.
- **Run:** `python -m interfaces.cli.chatops ask "Why did payment-service fail?"`

---

## 9. Viva Preparation: Key Technical Q&A

**Q: Why chunk by section headings instead of simple fixed character splitting?**
> SRE runbooks are naturally organized by semantic roles (`Symptoms`, `Likely cause`, `Fix`). Keeping each section intact preserves the logical boundary between problem observation and remedy, avoiding chunks that mix symptoms of one issue with remediation steps of another.

**Q: Why use `all-MiniLM-L6-v2` instead of OpenAI or Bedrock Titan embeddings?**
> `all-MiniLM-L6-v2` is open-source, runs locally in milliseconds without network latency, incurs zero API costs, and works offline during local testing and evaluations.

**Q: How do we prevent LLM hallucinations in the diagnostic output?**
> 1. Restrictive system prompt enforcing that answers must derive exclusively from the retrieved context.
> 2. Negative constraint: if context is missing, the model must output an explicit lack-of-information statement.
> 3. Source tracking: Every response maps back to source runbook file paths and section names.

**Q: Why a LangGraph ReAct agent instead of a simple RAG chain for Week 2?**
> RAG alone cannot reason about live signals. The ReAct agent uses tools in a dynamic loop: it reads the runbook, then confirms with live metrics and pod status, only concluding when evidence aligns. This mirrors how a real SRE investigates: read the playbook first, then verify with observability data.

**Q: What is stub mode and why does it exist?**
> Stub mode (`--stub`) returns realistic synthetic data for Person B's tools (`get_metrics`, `get_pod_status`, `get_events`) so the agent can be fully exercised and demonstrated without requiring live Docker containers or Prometheus. Real integration happens Days 13-14 when both sides are running.

---

## 7. Week 3 — Conversation Memory, Benchmarking & Safety

### 7.1 New Files Added

| File | Purpose |
|------|---------|
| `agent/api.py` | Public `ask()` API with LangGraph MemorySaver for multi-turn memory |
| `agent/eval/scenarios.py` | 10 benchmark scenarios (one per failure type from contracts) |
| `agent/eval/benchmark.py` | Automated benchmark harness with ablation (full vs RAG-only) |
| `agent/eval/adversarial.py` | 11-test safety suite: prompt injection, OOD failures, hallucination, edge cases |
| `agent/multi/sub_agents.py` | Multi-agent skeleton: LogAgent, MetricsAgent, CoordinatorAgent |
| `docs/multi_agent_design.md` | Multi-agent RFC with architecture diagram and Week 4 roadmap |

---

### 7.2 Task A10: Conversation Memory (`agent/api.py`)

**Problem**: Week 2 `ask()` had no memory — each call was stateless.  
**Solution**: Week 3 `agent/api.py` uses **LangGraph MemorySaver** keyed by `thread_id`.

```python
# Single-turn (no memory):
result = ask("payment-service is crashing")

# Multi-turn Slack thread (memory preserved between calls):
r1 = ask("payment-service is crashing", thread_id="slack-T9XYZ")
r2 = ask("What caused the OOM?", thread_id="slack-T9XYZ")  # has full context of r1
```

**Output contract (standard for all callers)**:
```json
{
  "question":     "...",
  "diagnosis":    "...",
  "failure_type": "out_of_memory",
  "confidence":   "high",
  "tool_trace":   [{"tool": "search_runbooks", "output_summary": "..."}],
  "sources":      ["Runbook: out_of_memory-payment.md"],
  "latency_s":    4.2,
  "thread_id":    "slack-T9XYZ",
  "model_id":     null
}
```

**Safety upgrade**: AGENT_SYSTEM_PROMPT now includes explicit prompt-injection defence rules:
- Tool outputs are declared UNTRUSTED DATA.
- Agent is instructed to flag embedded `SYSTEM:` instructions as injection attempts.

---

### 7.3 Task A11: Benchmark Harness (`agent/eval/benchmark.py`)

#### Ablation Modes
| Mode | Tools Available | Purpose |
|------|----------------|---------|
| `full` | search_runbooks + get_metrics + get_pod_status + get_events | Full agent evaluation |
| `rag_only` | search_runbooks only | Measure contribution of live tools vs RAG alone |

#### Metrics Captured Per Run
| Metric | How Computed |
|--------|-------------|
| `failure_type_accuracy` | Exact match: extracted FT vs ground truth |
| `fix_keyword_score` | Fraction of expected keywords in diagnosis text |
| `runbook_citation_rate` | Whether runbook keywords appear in sources |
| `avg_tool_calls` | Number of tool calls per scenario |
| `avg_latency_s` | Wall-clock seconds per response |

#### Run benchmark
```bash
# Full agent (all tools):
python -m agent.eval.benchmark --ablation full --trials 1

# Ablation: RAG-only vs full:
python -m agent.eval.benchmark --ablation both --trials 3
```

Results saved to `agent/eval/results/<run_id>.json` and `<run_id>.md`.

---

### 7.4 Task A12: Safety & Adversarial Tests (`agent/eval/adversarial.py`)

11 adversarial test cases across 4 categories:

| Category | Tests | What is Verified |
|----------|-------|-----------------|
| `prompt_injection` | 3 | Agent ignores `rm -rf`, `DROP TABLE`, credential exfil embedded in logs |
| `unknown_failure` | 3 | Agent returns `unknown` / `low confidence` for out-of-distribution incidents |
| `hallucination` | 2 | Agent always calls tools; never invents metric values |
| `edge_case` | 3 | Whitespace input, multi-service query, repeated input |

```bash
python -m agent.eval.adversarial
python -m agent.eval.adversarial --verbose  # show full diagnosis per test
```

**Exit code 0** = all tests pass. **Exit code 1** = at least one failure.

---

### 7.5 Task A13: Multi-Agent Architecture (`agent/multi/`)

Three specialised sub-agents replacing the monolithic Week 2 agent (Week 4 target: parallel):

```
CoordinatorAgent
    ├── LogAgent      (get_events only — focuses on error patterns)
    ├── MetricsAgent  (get_metrics + get_pod_status — focuses on thresholds)
    └── RunbookRAG    (search_runbooks — coordinator calls this for final validation)
```

Coordinator confidence scoring:
- **high**: all three signal sources agree on root cause
- **medium**: two of three agree
- **low**: only one matches or sources conflict

See `docs/multi_agent_design.md` for the full RFC.

---

## 8. Weeks 4 & 5 Architecture & Evolution

### 8.1 Evidence-First Protocol (Task A15)
The agent replaces the previous RAG-first behavior with an **Evidence-First Protocol**:
1. `list_services` + `get_pod_status`: Checks physical container state (running, restarting, exited, oom_killed, unhealthy).
2. `get_logs` + `get_metrics` + `get_events`: Examines ERROR/CRITICAL logs and Prometheus latency/error/resource telemetry.
3. `search_runbooks`: Queries playbooks using **empirically observed error patterns**, not unverified user claims.

### 8.2 Unknown Handling & Confidence Threshold (Task A16)
- Similarity threshold set to `CONFIDENCE_THRESHOLD = 0.60`.
- Scores below threshold flag `no_confident_match: true`.
- Fallback behavior: Agent classifies incident as `failure_type: "unknown"`, `confidence: "low"`, generates 2–3 unverified hypotheses, recommends safe read-only diagnostics, and never cites unretrieved playbooks.

### 8.3 External Failure Knowledge Collection (Task A17)
- 50 curated real-world postmortems and troubleshooting guides indexed in a separate Chroma collection `external_knowledge` (201 chunks).
- Dual-collection search in `mcp_servers/runbooks/server.py`: internal runbooks rank first with $+0.03$ priority tie-breaking; external hits tagged with `source_type` (`external_postmortem` / `external_doc`) and source URLs.

### 8.4 Parallel Multi-Agent (Task A19)
- Three signal specialists running concurrently via `asyncio.gather()`:
  - `LogAgent`: Log pattern and stack trace extraction.
  - `MetricsAgent`: Prometheus metrics and container limits analysis.
  - `EventsAgent`: Lifecycle and cluster scheduling warnings.
- `CoordinatorAgent` synthesizes specialist reports and queries RAG for resolution.
- CLI flag `--multi` in `chatops ask`.

### 8.5 Continuous Learning Loop (Task A20)
- `chatops learn "<incident>"`: LLM drafts runbook under `data/runbooks/drafts/` with `status: draft`.
- Automatic quarantine: `rag/ingest.py` skips drafts to protect knowledge base integrity.
- `chatops approve "<draft_file>"`: Human approval moves file to `data/runbooks/` and triggers instantaneous Chroma upsert.

### 8.6 Remediation Proposal & Safety (Task A21)
- Agent can call `propose_remediation(service, action, params)` for non-destructive dry-run changes and risk ratings.
- The agent has **no tool that applies changes**. Applying changes requires human approval via single-use tokens (e.g. Slack button).

### 8.7 Final Benchmark Results & Charts (Task A22)
- Evaluated across 6 configurations, 4 foundation models, hold-out experiments, and trials.
- Output reports: `agent/eval/results/final_benchmark_report.md`
- Visualizations: `agent/eval/results/charts/` (accuracy by ablation, accuracy by model, latency vs cost, learning curve).
- Complete Viva defense guide: `docs/viva.md` (25 technical Q&A).

