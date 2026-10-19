# ChatOps Agent & RAG Architecture (Person A - Week 1 Deliverables)

This document records the design decisions, implementation details, benchmarking results, and tuning parameters for the **Person A (Brain)** side of the ChatOps SRE agent.

---

## 1. Architecture Overview

Person A owns the reasoning and diagnostic core:
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

## 3. Runbooks & Vector Store (Task A2)

### Runbooks (`data/runbooks/`)
6 concrete incident runbooks were authored strictly adhering to `contracts/runbook_format.md` and `contracts/failure_types.md`:
1. `out_of_memory-payment.md`: Container OOMKilled, exit code 137, `/leak` endpoint memory exhaustion.
2. `bad_config-order.md`: Missing `PAYMENT_SERVICE_URL`, exit code 1, critical startup failure.
3. `health_check_failure-inventory.md`: Injected `health_fail` toggle, HTTP 500, Docker unhealthy state.
4. `db_timeout-payment.md`: PostgreSQL database timeout after 5s, pool exhaustion.
5. `dependency_failure-order.md`: Downstream payment-service connection refused, cascading 502/500 errors.
6. `cpu_saturation-any.md`: High CPU utilization, event loop lag, p95 latency spikes above 2000ms.

### Ingestion & Chunking Strategy
- **Chunking Algorithm:** Parses markdown by `##` headers (`Symptoms`, `Likely cause`, `How to confirm`, `Fix`, `Prevention`).
- **Length Overflow Windowing:** Sections exceeding 600 characters are sub-chunked with a 100-character overlap along sentence/newline boundaries.
- **Context Enrichment:** Prepends runbook title, target service, and section name to every chunk.
- **Embedding:** `sentence-transformers` with `all-MiniLM-L6-v2` (384 dimensions, zero cloud cost, local CPU execution).
- **Storage:** Persistent Chroma DB at `chroma_db/` (32 total chunks indexed in 0.35s).
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

## 5. Retrieval Evaluation & Tuning (Task A4)

Evaluated using `rag/eval/run_eval.py` on 10 realistic SRE incident questions in `rag/eval/questions.yaml`:

### Results Matrix
| Metric | Result | Target | Status |
|---|---|---|---|
| **Hit Rate @ Top-1** | **90.0%** (9/10) | ≥ 80% | **PASSED** |
| **Hit Rate @ Top-3** | **100.0%** (10/10) | ≥ 90% | **PASSED** |
| **Mean Reciprocal Rank (MRR)** | **0.950** | ≥ 0.85 | **PASSED** |

### Detailed Evaluation Breakdown
| ID | Incident Query | Expected Runbook | Top Retrieved Runbook | Rank | Hit@1 | Hit@3 |
|---|---|---|---|---|---|---|
| 1 | Payment-service exit code 137 | `out_of_memory-payment.md` | `dependency_failure-order.md` | #2 | ✗ | ✓ |
| 2 | Memory climbing monotonically | `out_of_memory-payment.md` | `out_of_memory-payment.md` | #1 | ✓ | ✓ |
| 3 | Missing PAYMENT_SERVICE_URL | `bad_config-order.md` | `bad_config-order.md` | #1 | ✓ | ✓ |
| 4 | Order container exits with code 1 | `bad_config-order.md` | `bad_config-order.md` | #1 | ✓ | ✓ |
| 5 | Inventory /health returning 500 | `health_check_failure-inventory.md` | `health_check_failure-inventory.md` | #1 | ✓ | ✓ |
| 6 | Reset health_fail toggle | `health_check_failure-inventory.md` | `health_check_failure-inventory.md` | #1 | ✓ | ✓ |
| 7 | DB connection timed out after 5s | `db_timeout-payment.md` | `db_timeout-payment.md` | #1 | ✓ | ✓ |
| 8 | Cannot connect to postgres port 5432 | `db_timeout-payment.md` | `db_timeout-payment.md` | #1 | ✓ | ✓ |
| 9 | Failed to call payment-service | `dependency_failure-order.md` | `dependency_failure-order.md` | #1 | ✓ | ✓ |
| 10 | CPU usage 100% and latency spikes | `cpu_saturation-any.md` | `cpu_saturation-any.md` | #1 | ✓ | ✓ |

### Tuned Parameters
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (Cosine / L2 distance).
- **Max Chunk Size:** 600 characters.
- **Chunk Overlap:** 100 characters.
- **Top-K Retrieval:** 3 chunks.
- **Similarity Threshold:** Normalized score > 0.60.

---

## 6. Viva Preparation: Key Technical Q&A

**Q: Why chunk by section headings instead of simple fixed character splitting?**
> SRE runbooks are naturally organized by semantic roles (`Symptoms`, `Likely cause`, `Fix`). Keeping each section intact preserves the logical boundary between problem observation and remedy, avoiding chunks that mix symptoms of one issue with remediation steps of another.

**Q: Why use `all-MiniLM-L6-v2` instead of OpenAI or Bedrock Titan embeddings?**
> `all-MiniLM-L6-v2` is open-source, runs locally in milliseconds without network latency, incurs zero API costs, and works offline during local testing and evaluations.

**Q: How do we prevent LLM hallucinations in the diagnostic output?**
> 1. Restrictive system prompt enforcing that answers must derive exclusively from the retrieved context.
> 2. Negative constraint: if context is missing, the model must output an explicit lack-of-information statement.
> 3. Source tracking: Every response maps back to source runbook file paths and section names.
