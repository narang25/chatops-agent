# ChatOps Project: Person A Brief (LLM, RAG, Agent, CLI)

> How to use this file: it lives in the repo root. Tell your IDE agent:
> "Read PERSON_A_BRIEF.md fully, then read everything in contracts/. We are doing Week 1 only. Follow the folder ownership and git rules strictly and ask before doing anything outside Week 1."

---

## 1. What we are building

An open-source **AI SRE / ChatOps agent**. When a service fails, an engineer asks "why did payment-service fail?" in a CLI (Slack later). The agent searches runbooks and past incidents (RAG), pulls **live metrics and container status through MCP tools**, reasons with an LLM, and replies with a **cited diagnosis and a suggested fix**.

Why it is more than a chatbot over data (our answer to the professor):
1. A **tool-using agent over MCP**, not a document chatbot.
2. **Static knowledge plus live signals** used together.
3. **Explainable**: every answer cites its sources.
4. Later: **multi-agent diagnosis**, **approval-gated remediation with verification and rollback**, and a **chaos-based benchmark** that scores the agent automatically.

```
 Engineer (CLI now, Slack later)
            |
            v
     Agent (YOU)  <-- LLM (AWS Bedrock, Ollama fallback)
        |       \
        |        +--> search_runbooks (MCP server, YOU)   --> Chroma vector DB
        +-----------> get_metrics, get_pod_status, get_events (MCP servers, Person B)
```

**You own the brain:** LLM setup, RAG over runbooks, the agent, the CLI, and the `search_runbooks` MCP server. **Person B owns the world the agent investigates:** sample services, monitoring, failure injection, and the metrics and status MCP servers.

---

## 2. Rules for the IDE agent

### Folder ownership (the main way we avoid merge conflicts)
Edit only YOUR files. Never touch Person B's folders.

| Yours (A) | Person B's | Shared |
|---|---|---|
| `agent/` | `sample_apps/` | `contracts/` (change only via a PR both approve) |
| `rag/` | `infra/` | |
| `mcp_servers/runbooks/` | `mcp_servers/prometheus/` | |
| `interfaces/cli/` | `mcp_servers/kubernetes/` | |
| `data/runbooks/` | `interfaces/slack/` | |
| `docs/agent.md`, `README.md` | `data/incident_logs/`, `docs/infra.md` | |
| `requirements-agent.txt` | `requirements-infra.txt` | |
| `.env.agent.example` | `.env.infra.example` | |

Also: no shared `utils.py` at the repo root; keep helpers inside your own folders.

### Git rules
- Never commit to `main`. Branches: `feat/a-<short-name>` (e.g. `feat/a-rag-ingest`).
- Start each session with `git pull --rebase origin main`.
- Commit small, push at least daily, open a PR for each merge, Person B reviews, merge the same day if possible.
- Never commit secrets: `.env*` (except `*.example`), AWS keys, `chroma_db/`.

### Working style
- One task at a time. After each task, show how to run and verify it, then wait.
- Simple, readable, commented code. We must be able to explain every part in the viva.
- Each folder you create gets a short README.

---

## 3. Contracts you code against

Read `contracts/` first. The important ones for you:
- `runbook_format.md`: the Markdown + front-matter format your runbooks must follow.
- `failure_types.md`: the allowed `failure_type` values (shared with Person B's incident files).
- `mcp_tools.md`: the shape of `search_runbooks` (yours) and Person B's three tools.
- `logs.md`, `metrics.md`, `incident_meta.md`: what Person B's services produce, which you need to know when writing runbooks and the agent prompt.

Until Person B's real logs arrive (end of Week 1), write runbooks from your own knowledge and use hand-written sample logs in the `logs.md` format.

---

## 4. WEEK 1 (Days 2 to 7): your tasks

Goal: you can ask a question in a Python script and get a **cited answer from runbooks**, using Bedrock (or Ollama). No connection to Person B's tools yet.

### Task A1 (Day 2): LLM connection
- `agent/config.yaml`: `provider` (`bedrock` or `ollama`), `model_id`, `region`, `temperature`.
- `agent/llm.py`: `get_llm()` returns `ChatBedrockConverse` (from `langchain-aws`) or `ChatOllama` based on config. Swapping models must mean changing one line of config.
- `agent/scripts/smoke_llm.py`: sends "Say hello in one sentence" and prints the reply and which model answered.
- Credentials come from `.env.agent` or `aws configure`, never from code.
- Suggested starting models: `openai.gpt-oss-120b-1:0` on Bedrock (verify the exact ID and availability in your Bedrock console for your region), and a small local Ollama model as fallback.

Check: smoke test runs against Bedrock, and also against Ollama by changing config only.

### Task A2 (Days 3 to 4): Runbooks and ingestion
- Write **5 to 6 runbooks** in `data/runbooks/` following `contracts/runbook_format.md`. Week 1 topics: out of memory (OOMKilled), bad or missing config, failed health check, crash loop, database connection timeout, high latency. Make them concrete: real log messages, real commands (`docker inspect`, PromQL), clear fix steps.
- `rag/ingest.py`: load runbooks, read front-matter (`python-frontmatter`), chunk by section headings (fall back to ~600 characters with overlap), embed, store in Chroma at `chroma_db/` (gitignored).
- Embeddings for Week 1: `sentence-transformers` `all-MiniLM-L6-v2` (free, local, no AWS dependency).
- Store metadata on each chunk: `title`, `source` (file path), `failure_type`, `service`, `section`.
- Re-running ingest must not create duplicates.

Check: `python rag/ingest.py` reports chunk counts; a similarity search for "container killed out of memory" returns the OOM runbook first.

### Task A3 (Days 5 to 6): RAG chain with citations
- `rag/chain.py`: question in, top-k chunks retrieved, LLM answers using ONLY that context, output includes the answer and a list of sources (title and source path).
- Prompt rules: if the context does not contain the answer, say so; never invent fixes; always list the runbook used.
- `rag/scripts/ask.py "why is my container restarting with exit code 137?"` prints answer plus sources.

Check: 5 hand-written questions return sensible, cited answers.

### Task A4 (Day 7): Evaluate and tune
- `rag/eval/questions.yaml`: 10 questions, each with the runbook that should be retrieved.
- `rag/eval/run_eval.py`: prints hit rate at top-1 and top-3.
- Tune chunk size and top-k until retrieval is good. Write results and settings in `docs/agent.md`.
- Pull Person B's real incident logs from `data/incident_logs/` once they are merged and update runbooks to match.

### Week 1 definition of done
- [ ] LLM switchable between Bedrock and Ollama by config
- [ ] 5 to 6 runbooks in the contract format
- [ ] Ingestion and retrieval working, no duplicates on re-run
- [ ] RAG chain answers with citations
- [ ] Retrieval evaluation on 10 questions recorded in `docs/agent.md`
- [ ] Everything merged to `main` through PRs

---

## 5. WEEK 2 (Days 8 to 14): preview

| Days | Task |
|---|---|
| 8 | Grow runbooks to about 10, matching Person B's real failures (use her logs and `.meta.json` files) |
| 9 | `mcp_servers/runbooks/`: `search_runbooks` MCP server (FastMCP) wrapping your retrieval, returning the contract shape |
| 10 to 11 | `agent/`: a single tool-calling agent (LangGraph or LangChain) that can call `search_runbooks` plus Person B's `get_metrics`, `get_pod_status`, `get_events`. System prompt: investigate first, cite evidence, never claim a cause without a supporting tool result |
| 12 | `interfaces/cli/`: `chatops ask "why did payment-service fail?"` using Typer, with readable output (diagnosis, evidence, suggested fix, sources) |
| 13 to 14 | Integrate with Person B: break a service live and check the agent diagnoses it. Fix bugs in small PRs. Record a fallback demo video |

---

## 6. WEEKS 3 to 5: roadmap

- **Week 3:** support Person B's Minikube move (the agent should not need changes if the tool shapes stay the same). Add conversation memory in the CLI. Help wire the agent into her Slack bot (she owns `interfaces/slack/`, you expose a clean `ask(question) -> answer` function in `agent/`).
- **Week 4:** **multi-agent diagnosis** with LangGraph: specialist agents (logs, metrics, events, changes) each propose a hypothesis with evidence, and a coordinator ranks them with a confidence score. Add the "what changed?" tool usage once her GitHub MCP server exists. Build the **benchmark scorer**: for each incident in `data/incident_logs/`, compare the agent's answer with `.meta.json` ground truth.
- **Week 5:** the agent side of **safe remediation**: propose a fix, show a dry run, wait for approval, then verify with metrics and roll back if worse. Run the final benchmark across several Bedrock models and configurations (RAG only, RAG plus live metrics, full multi-agent) and write the results section of the report. Optional if time allows: self-learning runbooks.

If time gets tight, cut in this order: self-learning runbooks, "what changed?", auto-rollback. Keep the benchmark and approval-gated remediation.

---

## 7. First message to send to your IDE agent

> Read PERSON_A_BRIEF.md fully, then read every file in contracts/. I am Person A. We are doing Week 1 only. Start with Task A1 (LLM connection): set up a Python virtual environment, install from requirements-agent.txt, create agent/config.yaml and agent/llm.py, and a smoke test script. Show me how to run it and wait. Follow the folder ownership and git rules strictly and do not touch Person B's folders.
