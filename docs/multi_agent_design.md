# Multi-Agent Architecture Design  (Week 3 — Task A13)

> **Status**: RFC / Skeleton — Week 4 target for full parallel execution.  
> **Owner**: Person A (Brain)

---

## 1. Motivation

The Week 2 monolithic ReAct agent handles all signal domains (logs, metrics,
runbooks, pod status) in a single LangGraph graph.  While this works for
simple incidents, it has three weaknesses:

| Weakness | Impact |
|----------|--------|
| Single system prompt is large → higher hallucination risk | Diagnosis quality degrades for complex multi-signal incidents |
| Sequential tool calls → higher latency | ~4 tool calls × 2-5s each = 8-20s per query |
| Adding new signal domains (traces, SLO budget) bloats the agent | Maintenance burden grows linearly |

---

## 2. Architecture

```
User Query (via Slack / CLI)
        │
        ▼
 ┌─────────────────────┐
 │  CoordinatorAgent   │  ← synthesises all sub-agent outputs
 └─────────────────────┘
        │ spawns (parallel in Week 4)
        ├────────────────────┬──────────────────────┐
        ▼                    ▼                       ▼
 ┌──────────────┐  ┌──────────────────┐  ┌────────────────────┐
 │  Log Agent   │  │  Metrics Agent   │  │  Runbook RAG       │
 │ (get_events) │  │ (get_metrics +   │  │ (search_runbooks)  │
 └──────────────┘  │  get_pod_status) │  └────────────────────┘
                   └──────────────────┘
```

### 2.1 Sub-Agent Responsibilities

| Agent | Tools | System Prompt Focus | Output |
|-------|-------|---------------------|--------|
| **LogAgent** | `get_events` | Stack traces, error codes, event ordering | `log_patterns`, `error_codes`, `suspicious_events` |
| **MetricsAgent** | `get_metrics`, `get_pod_status` | Threshold violations, trends, OOM | `metric_anomalies`, `pod_state`, `thresholds_exceeded` |
| **CoordinatorAgent** | `search_runbooks` | Synthesis + confidence scoring | Final structured diagnosis |

### 2.2 Coordinator Confidence Scoring

```
confidence = "high"   if log_signals + metric_signals + runbook_signals all agree
confidence = "medium" if two of three signal sources agree
confidence = "low"    if only one signal source matches or sources conflict
```

---

## 3. Implementation Plan

### Week 3 (current — skeleton)
- [x] `agent/multi/sub_agents.py` — all three agents defined and orchestrated sequentially
- [x] `docs/multi_agent_design.md` — this RFC

### Week 4 (parallel execution)
- [ ] Convert `multi_agent_ask()` to `async` with `asyncio.gather(log_agent, metrics_agent)`
- [ ] Add `agent/multi/coordinator.py` with LangGraph supervisor pattern
- [ ] Wire into `agent/api.py` as `mode="multi"` parameter
- [ ] Benchmark latency improvement: sequential vs parallel

---

## 4. Key Design Decisions

### 4.1 Why LangGraph over raw asyncio?

LangGraph's `StateGraph` provides:
- Typed state passing between agents
- Built-in checkpointing (MemorySaver) for multi-turn memory
- Easy debugging via `langgraph studio`

### 4.2 Why specialise rather than give all tools to one agent?

| Property | Monolithic | Multi-Agent |
|----------|-----------|-------------|
| System prompt size | Large (~500 tokens) | Small (~150 tokens each) |
| Hallucination risk | Higher | Lower |
| Latency | Sequential | Parallel (Week 4) |
| Explainability | One black box | Per-signal reasoning |

### 4.3 Coordinator Trust Model

Sub-agent outputs are treated as **structured intermediate data**, not
as final answers.  The Coordinator still calls `search_runbooks` once to
cross-validate before producing the final diagnosis.

---

## 5. Files

| File | Purpose |
|------|---------|
| `agent/multi/__init__.py` | Package marker |
| `agent/multi/sub_agents.py` | LogAgent, MetricsAgent, CoordinatorAgent definitions + sequential orchestrator |
| `docs/multi_agent_design.md` | This RFC |

---

## 6. Example Run (Week 3 sequential mode)

```python
from agent.multi.sub_agents import multi_agent_ask

result = multi_agent_ask(
    question="payment-service is OOM-killing. What is wrong?",
    service="payment-service",
)
print(result["final_diagnosis"])
```
