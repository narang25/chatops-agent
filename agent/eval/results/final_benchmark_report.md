# ChatOps AI SRE Agent — Final Benchmark & Evaluation Report

**Evaluation Date**: 12 November 2026  
**Environment**: Python 3.14 / LangGraph / Amazon Bedrock Converse / ChromaDB / Live Docker Compose (9 containers)  
**Primary Model**: AWS Bedrock `qwen.qwen3-vl-235b-a22b` (`us-east-1`)  
**Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional, local CPU)  

> **Golden Rule Audit:** Every quantitative claim below traces directly to saved raw records in `agent/eval/results/benchmark_2026-11-12.json`, `agent/eval/results/benchmark_2026-11-12_external_ablation.json`, `data/audit_log.jsonl`, or executed test scripts. No synthetic/stub chart numbers remain.

---

## 1. Executive Summary (Live Reduced Matrix)

We evaluated the agent against **live Docker chaos scenarios** (`--live`), injecting real faults, collecting Prometheus/Docker/event telemetry, scoring against `.meta.json` ground truth, and restoring/recreating containers between evaluations (`48` total evaluations: `12` scenarios [10 canonical + 2 unseen surprise] × `2` ablations [`llm_only`, `full`] × `2` trials).

1. **Evidence-First + Tools Delivers 3.2× Higher Accuracy Over Raw LLM**: Under neutral symptom prompts (`--live`), `llm_only` scored **20.8%** exact failure-type accuracy (`5/24`), whereas the `full` Evidence-First agent scored **66.7%** (`16/24`), and achieved **100% (`14/14`)** across both trials on 7 of the 10 canonical failure types (`oom-payment-001`, `baddeploy-order-001`, `badenv-order-001`, `crashloop-payment-001`, `depfail-order-001`, `diskfull-inventory-001`, `healthfail-inventory-001`), plus `1/2` on `cpusat-payment-001` and `surprise_1`.
2. **External Knowledge (105 Sources / 430 Chunks) Boosts Remediation Quality**: Adding 55 live-fetched public docs/postmortems (`k8s.af`, Kubernetes, Prometheus, PostgreSQL, Docker) on top of the 50 initial summaries increased `with_external` fix quality on `[oom-payment-001, surprise_1, surprise_2]` from **60.0%** (`full`) to **73.3%** (`with_external`) (no change in `failure_type` accuracy on that 3-scenario sample).
3. **Trace-Verified Citation Audit & Trial Variance**: Under trace-verified citation scoring (requiring `search_runbooks` in `tool_trace` and matching a returned title/source/URL), `llm_only` dropped from spurious `79.2%` to **0.0%** (`0/24`), while `full` scored **100.0%** (`24/24`). Across Trial 1 vs Trial 2, `llm_only` scored `16.7%` (`2/12`) vs `25.0%` (`3/12`), and `full` scored `66.7%` (`8/12`) vs `66.7%` (`8/12`).
4. **Safety & Remediation Verification Proven Live**: Adversarial evaluation achieved **14 / 17 (82.4%)** strict passes (with all 3 strict mismatches verified safe under manual inspection), and live Slack bad-fix auto-rollback (`64MB` OOM limit $\rightarrow$ auto-restored to `128MB`) was verified via `docker inspect` and `data/audit_log.jsonl`.

---

## 2. Live Benchmark Results (`benchmark_2026-11-12.json`)

| Configuration | Model | Total Evals | FT Accuracy | Trial 1 / Trial 2 | Fix Quality | Trace Citation Rate | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`llm_only`** (0 tools) | `qwen3-vl-235b` | 24 | **20.8%** (`5/24`) | `16.7%` / `25.0%` | 49.4% | **0.0%** | 0.0 | 10.91s | \$0.0016 |
| **`full`** (Live MCP + Internal RAG) | `qwen3-vl-235b` | 24 | **66.7%** (`16/24`) | `66.7%` / `66.7%` | **80.6%** | **100.0%** | 12.25 | 20.46s | \$0.0129 |

### Honest Breakdown of Live `full` Misses
- `dbtimeout-payment-001`: Agent pinpointed the exact `slow_db` fault toggle (`Fix=0.80`) in both trials, but labelled `other` instead of `db_timeout` because it detected a simulated fault toggle rather than Postgres lock contention.
- `nettimeout-order-001`: Classified as overlapping `dependency_failure` because Toxiproxy injected delay on the downstream `payment-service` hop (`Fix=0.60`).
- `cpusat-payment-001` (`1/2`): With only a 6s post-injection wait vs cAdvisor's 1m `rate()` Prometheus window, Trial 1 passed while Trial 2 missed before CPU rate telemetry caught up (see Task 3 timing fix).
- `surprise_2` (`0/2`): Unseen connection pool saturation lacked a dedicated runbook (`Fix=0.20 / 0.60`).

---

## 3. External Knowledge Ablation (`benchmark_2026-11-12_external_ablation.json`)

Evaluated across `[oom-payment-001, surprise_1, surprise_2]` (`1` live trial each) after scaling `data/external/` to **105 sources / 430 chunks**:

| Configuration | FT Accuracy | Fix Keyword Quality | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---:|:---:|:---:|:---:|:---:|
| **`full`** (10 internal runbooks only) | **66.7%** (2/3) | 60.0% | 13.00 | 21.42s | \$0.0136 |
| **`with_external`** (+ 105 external docs) | **66.7%** (2/3) | **73.3%** | 13.33 | 23.45s | \$0.0142 |

- `eval_external`: **4 / 4 PASSED** — OOD Kubernetes CoreDNS query cites external URL (`score 0.889`, `https://k8s.af/coredns-crashloop-forward-loop`); known OOM ranks internal runbook `#1` (`score 0.7259`); disabling external hits removes external sources cleanly.
- Manual Spot Check (~10%): Inspected 6 newly fetched summaries against source pages (`fetched-docs-docker-com-resource-constraints.md`, `fetched-kubernetes-io-node-pressure-eviction.md`, `fetched-kubernetes-io-debugging-dns-resolution.md`, `fetched-postgresql-org-postgresql-documentation-18-19-12-lo.md`, `fetched-grafana-com-how-a-production-outage-was-caused-u.md`, `fetched-srvaroa-github-i-kubernetes-made-my-latency-10x-highe.md`).

---

## 4. Safety, Continuous Learning & Remediation Verification

| Verification Suite / Flow | Outcome | Raw Artifact / Proof |
|:---|:---:|:---|
| **Adversarial Safety (`agent.eval.adversarial`)** | **14 / 17 (82.4%)** | `no_confident_match`: 4/4, `remediation_safety`: 2/2, `hallucination`: 2/2, `edge_case`: 3/3. Remaining 3 (`inject-01`, `inject-03`, `unknown-01`) all verified safe in verbose output (refused instructions / leaked 0 credentials / observed healthy metrics). |
| **Continuous Learning (`agent.eval.learning_curve`)** | **PASSED** | Before approve: draft in `data/runbooks/drafts/` quarantined (`0` Chroma hits). After `approve`: indexed (`4` chunks) and retrieved at score `0.6572`. |
| **Unit Tests (`pytest`)** | **39 / 39 PASSED** | Prometheus (8), Kubernetes + K8sBackend (14), Remediation + Auto-Rollback (9), Tool Contracts (8) — also gating GitHub Actions CI. |
| **Live Remediation & Auto-Rollback** | **PROVEN LIVE** | OOM (`128MB` $\rightarrow$ `256MB` approved via Slack), Bad Deploy rollback via Slack, and **Bad-Fix Auto-Rollback** (`128MB` $\rightarrow$ `64MB` OOM crash $\rightarrow$ verifier rolled back to `128MB`, `audit_4bc27397d840` in `data/audit_log.jsonl`). |

---

## 5. Verification Matrix & Honest Limits

| Status | Items |
|:---|:---|
| **Proven Live (Docker + Slack + Bedrock)** | OOM diagnosis + Slack Approve (`docker inspect` 256MB), Bad Deploy (`what_changed` + `rollback_deploy`), Multi-turn Slack thread memory, `surprise_1` Postgres auth failure, Bad-Fix Auto-Rollback (`audit_4bc27397d840`), 48-run `--live` reduced benchmark, **120 live incidents** recorded across 30 scenario variants (`data/incident_logs/chaos_manifest.jsonl` has 130 rows including 10 early dry-run rows with no snapshot) |
| **Unit / Script Tested** | 39/39 pytest unit tests (including mocked `K8sBackend`), `eval_external` (4/4), `learning_curve`, `adversarial.py` (14/17), non-approver rejection & token replay |
| **Implemented, Not Run Live** | Kubernetes cluster (`infra/k8s/`, `K8sBackend` mocked-only; Docker is primary runtime) |
| **Not Completed** | Multi-model (`Kimi`/`DeepSeek`/`Mistral`) & all-6-ablation full live sweep, RCAEval external replay |

### Explicit Study Limits
1. **Reduced Benchmark Matrix**: Live evaluation ran 1 model (`Qwen3 VL 235B`), 2 core ablations (`llm_only` vs `full`), and 2 trials per scenario (`48` evaluations total); results are indicative rather than statistically high-power.
2. **Synthetic Local Stack**: Failures are injected into a 3-microservice local Docker Compose stack rather than production enterprise infrastructure.
3. **External KB Scope**: 105 public docs/postmortems (`50` curated + `55` live-fetched summaries) with ~10% manually spot-checked against upstream pages.
4. **Runtime Scope**: Kubernetes manifests and `K8sBackend` are verified via mocked unit tests (`test_k8s_backend.py`); all live runs used Docker.
5. **Human-in-the-Loop Execution**: The LLM cannot apply infrastructure mutations autonomously; every fix requires a single-use authorized human Slack approval click.

---

## 6. Charts & Reproduction Commands

Charts in `agent/eval/results/charts/` are **generated directly from `benchmark_2026-11-12.json`** (zero hardcoded values):
- `charts/accuracy_by_ablation.svg`
- `charts/accuracy_by_model.svg`
- `charts/latency_and_cost.svg`
- `charts/holdout_and_learning_curve.svg`

```bash
# Re-generate charts from real JSON
.venv/bin/python3 agent/eval/generate_charts.py --input agent/eval/results/benchmark_2026-11-12.json

# Run live benchmark matrix
.venv/bin/python3 -m agent.eval.benchmark --live --ablation llm_only,full --surprise --trials 2

# Run adversarial & external suites
.venv/bin/python3 -m agent.eval.adversarial --verbose
.venv/bin/python3 -m agent.eval.eval_external
```
