# ChatOps AI SRE Agent — Final Benchmark & Evaluation Report

**Evaluation Date**: 12–13 November 2026  
**Environment**: Python 3.14 / LangGraph / Amazon Bedrock Converse / ChromaDB / Live Docker Compose (9 containers)  
**Primary Model**: AWS Bedrock `qwen.qwen3-vl-235b-a22b` (`us-east-1`)  
**Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional, local CPU)  

> **Golden Rule Audit:** Every quantitative claim below traces directly to saved raw records in `agent/eval/results/benchmark_2026-11-12.json`, `agent/eval/results/benchmark_variants_2026-11-12.json`, `agent/eval/results/benchmark_2026-11-12_external_ablation.json`, `data/audit_log.jsonl`, or executed test scripts. No synthetic/stub chart numbers remain.

---

## 1. Executive Summary (Live Benchmark & Variants Matrix)

We evaluated the agent against **live Docker chaos scenarios** (`--live`), injecting real faults, collecting Prometheus/Docker/event telemetry, scoring against `.meta.json` ground truth, and restoring/recreating containers between evaluations:
- **Baseline Matrix**: `48` total evaluations (`12` scenarios [10 canonical + 2 unseen surprise] × `2` ablations [`llm_only`, `full`] × `2` trials).
- **Variant Extension**: `20` cross-service & parameterized variants (`full` ablation, 1 trial each, across all 3 microservices and varied severity thresholds).
- **Combined `full` Sample**: `44` live evaluations total.

1. **Evidence-First + Tools Delivers 3.2× Higher Accuracy Over Raw LLM**:
   - Under neutral symptom prompts (`--live`), `llm_only` scored **20.8%** (`5/24`) [95% Wilson CI: 9.2% – 40.5%].
   - The `full` Evidence-First agent scored **66.7%** (`16/24`) [95% Wilson CI: 46.7% – 82.0%], achieving **100% (`14/14`)** across both trials on 7 of the 10 canonical failure types (`oom-payment-001`, `baddeploy-order-001`, `badenv-order-001`, `crashloop-payment-001`, `depfail-order-001`, `diskfull-inventory-001`, `healthfail-inventory-001`), plus `1/2` on `cpusat-payment-001` and `surprise_1`.
   - On the 20-scenario variant benchmark (`benchmark_variants_2026-11-12.json`), `full` scored **55.0%** (`11/20`) [95% Wilson CI: 34.2% – 74.2%], with **74.8%** fix quality and **75.0%** trace citation rate.
   - Across the combined `full` evaluations ($N = 44$), diagnostic accuracy reached **61.4%** (`27/44`) [95% Wilson CI: 46.6% – 74.3%], with **78.0%** fix quality and **88.6%** (`39/44`) trace-verified citations.
2. **Trace-Verified Citation Audit**:
   - Citation scoring requires `search_runbooks` in `tool_trace` AND matching a returned source title, path, or URL.
   - `llm_only` scored **0.0%** (`0/24`), eliminating previous artifact hallucinated titles (which had scored 79.2% under loose string matching).
   - `full` scored **100.0%** (`24/24`) on the baseline and **75.0%** (`15/20`) on variants (**88.6%** combined).
3. **External Knowledge (105 Sources / 430 Chunks)**:
   - On `[oom-payment-001, surprise_1, surprise_2]`, adding 105 external docs yielded no measurable change in failure-type accuracy (**66.7% vs 66.7%**, 2/3 vs 2/3), and a small fix-quality gain (**60.0% to 73.3%**) on a tiny 3-scenario sample.
4. **Safety & Remediation Verification Proven Live**:
   - Adversarial evaluation achieved **14 / 17 (82.4%)** strict passes (with all 3 strict mismatches verified safe under manual inspection).
   - Live Slack bad-fix auto-rollback (`64MB` OOM limit $\rightarrow$ auto-restored to `128MB`) was verified via `docker inspect` and `data/audit_log.jsonl` (`audit_4bc27397d840`).

---

## 2. Live Benchmark Results

### 2.1 Baseline Matrix (`benchmark_2026-11-12.json`)

| Configuration | Model | Total Evals | FT Accuracy (95% Wilson CI) | Trial 1 / Trial 2 | Fix Quality | Trace Citation Rate | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`llm_only`** (0 tools) | `qwen3-vl-235b` | 24 | **20.8%** (`5/24`)<br>[9.2% – 40.5%] | `16.7%` / `25.0%` | 49.4% | **0.0%** (`0/24`) | 0.0 | 10.91s | \$0.0016 |
| **`full`** (Live MCP + RAG) | `qwen3-vl-235b` | 24 | **66.7%** (`16/24`)<br>[46.7% – 82.0%] | `66.7%` / `66.7%` | **80.6%** | **100.0%** (`24/24`) | 12.25 | 20.46s | \$0.0129 |

### 2.2 Parameterized & Cross-Service Variants (`benchmark_variants_2026-11-12.json`)

Evaluated across 20 distinct fault scenarios spanning all 3 services (`payment-service`, `order-service`, `inventory-service`):

| Configuration | Model | Total Evals | FT Accuracy (95% Wilson CI) | Fix Quality | Trace Citation Rate | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`full` (Variants)** | `qwen3-vl-235b` | 20 | **55.0%** (`11/20`)<br>[34.2% – 74.2%] | **74.8%** | **75.0%** (`15/20`) | 11.60 | 23.35s | \$0.0128 |

### 2.3 Combined Performance & Confidence Intervals

| Metric ($N = 44$) | Point Estimate | Exact Count | 95% Wilson Confidence Interval | Notes |
|:---|:---:|:---:|:---:|:---|
| **Combined FT Accuracy** | **61.4%** | `27 / 44` | **46.6% – 74.3%** | Non-overlapping with `llm_only` point estimate |
| **Combined Fix Quality** | **78.0%** | — | — | Weighted average across all 44 live runs |
| **Combined Trace Citations** | **88.6%** | `39 / 44` | **76.0% – 95.0%** | Trace-verified runbook citation rate |

> **Statistical Note on Sample Independence:** The Wilson 95% confidence intervals are computed using the score method with continuity adjustment under a standard binomial distribution. However, evaluations in the baseline matrix feature 2 repeated trials on the same 12 scenarios; repeated trials on identical chaos scenarios are not strictly independent observations. The reported confidence intervals characterize empirical measurement variation across the observed sample, while the true effective degrees of freedom are bounded by the unique scenario count (12 canonical/surprise + 20 variants = 32 distinct failure injections).

### 2.4 Diagnostic Label-Overlap & Miss Breakdown

Across both baseline and variant evaluations, non-matching diagnoses fall into clear, understandable technical patterns:
1. **`db_timeout` labelled `"other"` (`dbtimeout-payment-001`, `dbtimeout-*-v1`)**:
   The agent correctly queried `/admin/fault`, detected the active `slow_db` fault toggle, and recommended disabling it (`Fix=0.80`). It classified the failure as `"other"` because it observed an artificially injected administrative fault toggle rather than standard PostgreSQL lock contention or query planner stalls.
2. **`network_timeout` labelled `"dependency_failure"` or `"high_error_rate"` (`nettimeout-order-001`, `nettimeout-order-2500ms`)**:
   Because Toxiproxy injected network latency on the downstream `payment-service` hop, `order-service` timed out waiting for payment responses. The agent correctly pinpointed the downstream HTTP timeout and recommended fixing the downstream connection (`Fix=0.60–0.80`), but labelled the failure type under overlapping system labels (`dependency_failure` or `high_error_rate`).
3. **`dberror` labelled `"db_timeout"` (`dberror-payment-v1`, `dberror-order-v1`)**:
   In `chaos_variants.py`, the ground truth failure type was grouped as `high_error_rate` (kind: `db_error`). The agent pinpointed the database exception and labelled it `db_timeout` (scoring high fix remediation `0.60–0.80`).
4. **`surprise_2` miss (`0/2`)**:
   Unseen connection pool exhaustion (`postgres` max_connections=5 + connection leak) lacked a dedicated internal playbook and manifested as connection refused, which the agent diagnosed as general database connectivity failure rather than pool exhaustion (`Fix=0.20 / 0.60`).
5. **`cpusat-payment-001` timing artifact (`1/2`)**:
   With only a 6s post-injection wait vs cAdvisor's 1-minute `rate()` Prometheus window, Trial 1 passed while Trial 2 missed before CPU rate telemetry caught up. In `benchmark_2026-11-12_cpusat_timing.json` with an 80s continuous burn window, `full` achieved **100% (2/2)**.

---

## 3. External Knowledge Ablation (`benchmark_2026-11-12_external_ablation.json`)

Evaluated across `[oom-payment-001, surprise_1, surprise_2]` (`1` live trial each) after scaling `data/external/` to **105 sources / 430 chunks**:

| Configuration | FT Accuracy | Fix Keyword Quality | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---:|:---:|:---:|:---:|:---:|
| **`full`** (10 internal runbooks only) | **66.7%** (2/3) | 60.0% | 13.00 | 21.42s | \$0.0136 |
| **`with_external`** (+ 105 external docs) | **66.7%** (2/3) | **73.3%** | 13.33 | 23.45s | \$0.0142 |

- **Summary of Effect**: External knowledge produced **no measurable change in failure-type accuracy** (2/3 vs 2/3), but delivered a **small fix-quality gain (60.0% to 73.3%)** on this tiny 3-scenario sample.
- `eval_external`: **4 / 4 PASSED** — OOD Kubernetes CoreDNS query cites external URL (`score 0.889`, `https://k8s.af/coredns-crashloop-forward-loop`); known OOM ranks internal runbook `#1` (`score 0.7259`); disabling external hits removes external sources cleanly.
- Manual Spot Check (~10%): Inspected 6 newly fetched summaries against source pages (`fetched-docs-docker-com-resource-constraints.md`, `fetched-kubernetes-io-node-pressure-eviction.md`, `fetched-kubernetes-io-debugging-dns-resolution.md`, `fetched-postgresql-org-postgresql-documentation-18-19-12-lo.md`, `fetched-grafana-com-how-a-production-outage-was-caused-u.md`, `fetched-srvaroa-github-i-kubernetes-made-my-latency-10x-highe.md`).

---

## 4. Safety, Continuous Learning & Empirical Validations

| Verification Suite / Flow | Outcome | Raw Artifact / Proof |
|:---|:---:|:---|
| **Adversarial Safety (`agent.eval.adversarial`)** | **14 / 17 (82.4%)** | `no_confident_match`: 4/4, `remediation_safety`: 2/2, `hallucination`: 2/2, `edge_case`: 3/3. Remaining 3 (`inject-01`, `inject-03`, `unknown-01`) all verified safe in verbose output (refused instructions / leaked 0 credentials / observed healthy metrics). |
| **Continuous Learning (`agent.eval.learning_curve`)** | **PASSED** | Before approve: draft in `data/runbooks/drafts/` quarantined (`0` Chroma hits). After `approve`: indexed (`4` chunks) and retrieved at score `0.6572`. |
| **Incident Memory (Expansion A)** | **PASSED (100%)** | 120 live incident snapshots indexed in dedicated Chroma collection (`incident_memory`). Multi-archetype retrieval (4/4 PASS); hold-out demonstration successfully retrieves historical postmortem `badenv-order-001` (`score 0.7136`) with verified fix when internal runbook is withheld (`agent/eval/results/incident_memory_eval.json`). |
| **LogHub Generalization (Expansion B)** | **PASSED (97.6%)** | Evaluated Drain3 template miner on 2,000 public HDFS logs from LogHub (`data/external/loghub/HDFS_2k.log`), discovering 48 distinct templates in 0.007s with 97.6% compression (`agent/eval/results/loghub_eval.json`). |
| **Unit Tests (`pytest`)** | **39 / 39 PASSED** | Prometheus (8), Kubernetes + K8sBackend (14), Remediation + Auto-Rollback (9), Tool Contracts (8) — also gating GitHub Actions CI. |
| **Live Remediation & Auto-Rollback** | **PROVEN LIVE** | OOM (`128MB` $\rightarrow$ `256MB` approved via Slack), Bad Deploy rollback via Slack, and **Bad-Fix Auto-Rollback** (`128MB` $\rightarrow$ `64MB` OOM crash $\rightarrow$ verifier rolled back to `128MB`, `audit_4bc27397d840` in `data/audit_log.jsonl`). |

---

## 5. Verification Matrix & Honest Limits

| Status | Items |
|:---|:---|
| **Proven Live (Docker + Slack + Bedrock)** | OOM diagnosis + Slack Approve (`docker inspect` 256MB), Bad Deploy (`what_changed` + `rollback_deploy`), Multi-turn Slack thread memory, `surprise_1` Postgres auth failure, Bad-Fix Auto-Rollback (`audit_4bc27397d840`), 48-run baseline matrix, **20-run variant benchmark**, **120 live incidents** recorded across 30 scenario variants (`data/incident_logs/chaos_manifest.jsonl` has 130 rows including 10 early dry-run rows with no snapshot) |
| **Unit / Script Tested** | 39/39 pytest unit tests (including mocked `K8sBackend`), `eval_external` (4/4), `learning_curve`, `eval_incident_memory` (120 incidents, 4/4), `eval_loghub` (2,000 public logs), `adversarial.py` (14/17), non-approver rejection & token replay |
| **Implemented, Not Run Live** | Kubernetes cluster (`infra/k8s/`, `K8sBackend` mocked-only; Docker is primary runtime); **Multi-agent mode** (`agent/multi/sub_agents.py` with 3 parallel specialists LogAgent, MetricsAgent, EventsAgent via `asyncio.gather()` feeding a CoordinatorAgent) is implemented with stub specialist tools, but has not been benchmarked live across the Docker matrix. |
| **Not Completed** | Multi-model (`Kimi`/`DeepSeek`/`Mistral`) & all-6-ablation full live sweep, RCAEval external replay |

### Explicit Study Limits
1. **Single Evaluated Foundation Model on Live Runs**: All live Docker evaluations ran `Qwen3 VL 235B`; other models (`Mistral Large 3`, `DeepSeek V3.2`, `Kimi K2.5`) are wired via `agent/llm.py` but were not benchmarked on the live stack due to time and quota constraints.
2. **Two Primary Live Ablations**: Live comparisons focused on `llm_only` vs `full` (with a targeted 3-scenario external ablation); full 6-ablation live sweeps were not executed.
3. **Limited Trial Counts**: Baseline ran 2 trials per scenario and variants ran 1 trial per scenario; results are indicative rather than large-N statistical samples.
4. **Synthetic Local Stack**: Injections ran in a 3-microservice local Docker Compose stack rather than multi-node enterprise production infrastructure.
5. **Kubernetes Environment**: Kubernetes manifests and `K8sBackend` are verified via mocked unit tests (`test_k8s_backend.py`); all live evaluations executed on Docker Compose.
6. **External KB Hand-Verification**: 105 external postmortem/doc summaries are indexed, with ~10% (6 sources) hand-checked against upstream web pages.
7. **Human-in-the-Loop Execution**: The agent cannot apply infrastructure mutations autonomously; every remediation requires human Slack approval with single-use tokens.

---

## 6. Charts & Reproduction Commands

Charts in `agent/eval/results/charts/` are **generated directly from live JSON outputs** (zero hardcoded values):
- `charts/accuracy_by_ablation.svg`
- `charts/accuracy_by_model.svg`
- `charts/latency_and_cost.svg`
- `charts/holdout_and_learning_curve.svg`
- `charts/variants_by_category.svg`

```bash
# Re-generate charts from real JSON files
.venv/bin/python3 agent/eval/generate_charts.py

# Run live benchmark baseline matrix
.venv/bin/python3 -m agent.eval.benchmark --live --ablation llm_only,full --surprise --trials 2

# Run live 20-variant chaos benchmark
.venv/bin/python3 -m agent.eval.benchmark --variants --live --ablation full --trials 1

# Run adversarial, external, incident memory & LogHub suites
.venv/bin/python3 -m agent.eval.adversarial --verbose
.venv/bin/python3 -m agent.eval.eval_external
.venv/bin/python3 -m agent.eval.eval_incident_memory
.venv/bin/python3 -m agent.eval.eval_loghub
```
