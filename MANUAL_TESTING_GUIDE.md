# ChatOps SRE Agent — Comprehensive Manual Testing Guide (T11)

This document contains the step-by-step verification instructions for testing the entire system manually from top to bottom. Use this file as your checklist to test each component and record any errors or notes directly.

---

## Quick Reference: Two Ways to Test

1. **Automated Verification Runner (Runs in 1 Command):**
   ```bash
   ./run_manual_checks.py --all-auto
   ```
   *Runs all non-destructive automated checks across sections A through K and prints a PASS/FAIL summary table.*

2. **Step-by-Step Manual Execution:**
   Follow the sections below sequentially. Always run inside your repository virtual environment:
   ```bash
   cd /Users/nikhi/Desktop/Chatops/chatops-agent
   source .venv/bin/activate
   ```

---

## Results & Tracking Checklist

| Section | Check / Test Name | Status | Notes / Errors Observed |
|:---|:---|:---:|:---|
| **A** | Repository clean & in sync with `origin/main` | [ ] | |
| **A** | Secrets scan: no `.env` or credentials tracked | [ ] | |
| **A** | Pytest unit & integration suite (48 tests pass) | [ ] | |
| **A** | Ruff linting on core infra & MCP servers | [ ] | |
| **B** | All 9 Docker containers UP & healthy | [ ] | |
| **B** | Microservice health endpoints (8001, 8002, 8003) return 200 OK | [ ] | |
| **B** | Prometheus targets UP on `localhost:9090` | [ ] | |
| **B** | Grafana dashboard live on `localhost:3000` | [ ] | |
| **C** | Ingestion idempotence (62 internal + 430 external chunks) | [ ] | |
| **C** | Internal runbook priority (+0.03 boost on OOM) | [ ] | |
| **C** | External postmortem retrieval with URL (CoreDNS) | [ ] | |
| **C** | Confidence threshold fallback (`no_confident_match: true`) | [ ] | |
| **C** | External evaluation suite (`eval_external.py`, 4/4) | [ ] | |
| **D** | Bedrock LLM smoke test (Hello, tool call, no reasoning leak) | [ ] | |
| **E** | Scenario 1: `oom-payment-001` (Exit 137, OOM diagnosis) | [ ] | |
| **E** | Scenario 2: `badenv-order-001` (Exit 1, missing env var) | [ ] | |
| **E** | Scenario 3: `healthfail-inventory-001` (500 error, restart) | [ ] | |
| **E** | Scenario 4: `dbtimeout-payment-001` (3s delay, DB timeout) | [ ] | |
| **E** | Scenario 5: `depfail-order-001` (502 Gateway, downstream down) | [ ] | |
| **E** | Scenario 6: `cpusat-payment-001` (Throttling, p95 spike > 90s) | [ ] | |
| **E** | Scenario 7: `diskfull-inventory-001` (Errno 28, disk full) | [ ] | |
| **E** | Scenario 8: `nettimeout-order-001` (Toxiproxy delay, hop timeout)| [ ] | |
| **E** | Scenario 9: `baddeploy-order-001` (What changed, rollback deploy) | [ ] | |
| **E** | Scenario 10: `crashloop-payment-001` (Restarts > 3, crash loop) | [ ] | |
| **E** | Scenario 11: `surprise_1` (Unseen Postgres password failure) | [ ] | |
| **E** | Scenario 12: `surprise_2` (Unseen Connection pool exhaustion) | [ ] | |
| **F** | Evidence Gate: Tool trace calls status & logs before runbook | [ ] | |
| **F** | Healthy service check: reports "no problem found" | [ ] | |
| **F** | Nonexistent service check: reports service does not exist | [ ] | |
| **F** | Adversarial safety suite (`agent.eval.adversarial`, 14/17) | [ ] | |
| **G** | Slack bot connects via Socket Mode | [ ] | |
| **G** | Live Slack incident diagnosis card & buttons | [ ] | |
| **G** | Multi-turn Slack thread memory retains context | [ ] | |
| **G** | `/chatops` slash command works | [ ] | |
| **H** | Dry-run proposal: zero mutation in `docker inspect` | [ ] | |
| **H** | Authorized approval applies change cleanly | [ ] | |
| **H** | Bad-fix automatic rollback (`64m` limit $\rightarrow$ auto-restored) | [ ] | |
| **H** | Parameter tampering rejection (`expected_params` mismatch) | [ ] | |
| **H** | Unauthorized approver rejection (`unauthorized_approver`) | [ ] | |
| **H** | Token single-use enforcement (`invalid_or_used_token`) | [ ] | |
| **I** | `chatops learn` writes draft to `data/runbooks/drafts/` | [ ] | |
| **I** | Quarantined draft is NOT searchable | [ ] | |
| **I** | `chatops approve` publishes and re-indexes draft | [ ] | |
| **I** | Continuous learning curve script (`learning_curve.py`) | [ ] | |
| **J** | Incident memory telemetry retrieval (`eval_incident_memory.py` 4/4) | [ ] | |
| **J** | Hold-out generalisation test (`eval_incident_memory_generalisation.py` 3/3)| [ ] | |
| **J** | LogHub Drain3 log pattern clustering (48 templates from 2,000 lines)| [ ] | |
| **K** | Benchmark raw JSON files present in `agent/eval/results/` | [ ] | |
| **K** | Regenerate 5 SVG charts (`generate_charts.py`) | [ ] | |
| **L** | Demo script rehearsal (end-to-end rehearsal twice) | [ ] | |

---

## Detailed Step-by-Step Instructions

### Section A: Repository & CI
1. **Check Git Status:**
   ```bash
   git status
   ```
   *Expected:* `On branch main`, clean working tree.
2. **Scan for Tracked Secrets:**
   ```bash
   git ls-files | grep -i "\.env"
   ```
   *Expected:* Only `.env.agent.example` and `.env.infra.example`.
3. **Run Pytest Suite:**
   ```bash
   .venv/bin/pytest -v
   ```
   *Expected:* `48 passed` across `test_k8s_backend.py`, `test_server.py`, `test_evidence_gate.py`, and `test_tools.py`.
4. **Run Ruff Linting:**
   ```bash
   ruff check interfaces/slack/app.py infra/manage.py infra/failures/ mcp_servers/prometheus/server.py mcp_servers/kubernetes/server.py mcp_servers/kubernetes/backends/ --ignore E501,ANN,D,BLE001,EXE001,SIM,UP,S1,PLW,FURB,RUF
   ```
   *Expected:* `All checks passed!`

---

### Section B: Infrastructure Stack & Observability
1. **Start Docker Stack:**
   ```bash
   python infra/manage.py up
   python infra/manage.py ps
   ```
   *Expected:* 9 running containers: `payment-service`, `order-service`, `inventory-service`, `postgres`, `prometheus`, `grafana`, `cadvisor`, `toxiproxy`, `loadgen`.
2. **Test Health Endpoints:**
   ```bash
   curl -s http://localhost:8001/health && echo ""
   curl -s http://localhost:8002/health && echo ""
   curl -s http://localhost:8003/health && echo ""
   ```
   *Expected:* `{"status":"ok"}` on all three ports.
3. **Prometheus & Grafana:**
   - Prometheus Targets: Open `http://localhost:9090/targets` in browser. All targets should show **UP**.
   - Grafana Dashboard: Open `http://localhost:3000` (User: `admin`, Password: `admin`). Microservice traffic should show live request rates.

---

### Section C: Knowledge Base & Vector Retrieval
1. **Ingest Runbooks (Idempotence Test):**
   ```bash
   python rag/ingest.py
   python rag/ingest.py
   ```
   *Expected:* 62 internal chunks, 430 external chunks across 115 total documents. Zero duplicate chunks created.
2. **Search Internal Runbook (Priority Boost):**
   ```bash
   python rag/search.py "container killed exit code 137 out of memory"
   ```
   *Expected:* Top hit is `out_of_memory-payment.md` (`internal_runbook`).
3. **Search External Runbook (Source URL):**
   ```bash
   python rag/search.py "coredns crashloop forward loop detected"
   ```
   *Expected:* Returns `k8s-coredns-crashloop.md` citing `https://k8s.af/coredns-crashloop-forward-loop`.
4. **Search Gibberish (Confidence Threshold):**
   ```bash
   python rag/search.py "random nonexistent gibberish 12345"
   ```
   *Expected:* Returns empty list or `no_confident_match: true`.
5. **Run External RAG Suite:**
   ```bash
   python -m agent.eval.eval_external
   ```
   *Expected:* `4 / 4 PASSED`.

---

### Section D: Foundation Model Smoke Verification
1. **Run Smoke Test:**
   ```bash
   python agent/scripts/smoke_llm.py
   ```
   *Expected:* PASS for Hello generation, PASS for tool calling (`get_service_status`), and NONE for reasoning leakage.

---

### Section E: The 12 Chaos Failure Injections
For each scenario, run the injection, query the agent, and restore:

```bash
# 1. Out of Memory
python infra/failures/run_scenario.py run oom-payment-001
python -m agent.api "why is payment-service failing?"
python infra/failures/run_scenario.py restore

# 2. Bad Configuration
python infra/failures/run_scenario.py run badenv-order-001
python -m agent.api "what is wrong with order-service?"
python infra/failures/run_scenario.py restore

# 3. Health Check Failure
python infra/failures/run_scenario.py run healthfail-inventory-001
python -m agent.api "check health of inventory-service"
python infra/failures/run_scenario.py restore

# 4. Database Timeout
python infra/failures/run_scenario.py run dbtimeout-payment-001
python -m agent.api "investigate errors on payment-service"
python infra/failures/run_scenario.py restore

# 5. Dependency Failure
python infra/failures/run_scenario.py run depfail-order-001
python -m agent.api "why are orders failing with 502 Bad Gateway?"
python infra/failures/run_scenario.py restore

# 6. CPU Saturation (wait 90 seconds for metric aggregation)
python infra/failures/run_scenario.py run cpusat-payment-001
sleep 90
python -m agent.api "why is payment-service latency spiking?"
python infra/failures/run_scenario.py restore

# 7. Disk Full
python infra/failures/run_scenario.py run diskfull-inventory-001
python -m agent.api "inventory-service is failing to write files"
python infra/failures/run_scenario.py restore

# 8. Network Timeout
python infra/failures/run_scenario.py run nettimeout-order-001
python -m agent.api "order-service checkout calls are timing out"
python infra/failures/run_scenario.py restore

# 9. Bad Deploy
python infra/failures/run_scenario.py run baddeploy-order-001
python -m agent.api "what changed in order-service and why is it failing?"
python infra/failures/run_scenario.py restore

# 10. Crash Loop
python infra/failures/run_scenario.py run crashloop-payment-001
python -m agent.api "why is payment-service restarting repeatedly?"
python infra/failures/run_scenario.py restore

# 11. Surprise 1: Postgres Authentication Failure
python infra/failures/run_scenario.py run surprise_1
python -m agent.api "payment-service cannot process transactions"
python infra/failures/run_scenario.py restore

# 12. Surprise 2: Postgres Connection Pool Saturation
python infra/failures/run_scenario.py run surprise_2
python -m agent.api "payment-service reports connection refused"
python infra/failures/run_scenario.py restore
```
*After each restore, confirm `curl -s http://localhost:8001/health` returns `{"status":"ok"}`.*

---

### Section F: Agent Diagnostic Behaviour & Evidence Gate
1. **Evidence Gate Code Verification:**
   Inspect the tool trace printed by `python -m agent.api "why is payment-service failing?"`:
   - `get_pod_status` and `get_logs` must appear **before** `search_runbooks`.
   - If `search_runbooks` is called prematurely without evidence, it returns: `{"error": "gather evidence first: inspect pod status and logs for payment-service before consulting runbooks"}`.
2. **Healthy Service Check:**
   ```bash
   python -m agent.api "is inventory-service healthy?"
   ```
   *Expected:* Agent inspects telemetry, finds healthy status, and reports **no problem found**.
3. **Nonexistent Service Check:**
   ```bash
   python -m agent.api "why is billing-service down?"
   ```
   *Expected:* Agent lists services, detects that `billing-service` does not exist, and reports that honestly.
4. **Adversarial Safety Evaluation:**
   ```bash
   python -m agent.eval.adversarial --verbose
   ```
   *Expected:* `14 / 17 (82.4%)` strict passes. Prompt overrides and injection attempts are treated as literal text.

---

### Section G: Slack Bot & Multi-Turn Thread
1. **Start Slack Bot in Socket Mode:**
   ```bash
   python interfaces/slack/app.py
   ```
   *Expected:* `⚡️ Bolt app is running!`.
2. **Ask Incident in Channel:**
   ```text
   @chatops-sre why is payment-service failing?
   ```
   *Expected:* Interactive diagnosis card with root cause, observed evidence, runbook citation, and remediation proposal buttons.
3. **Multi-Turn Thread Follow-up:**
   In the generated Slack thread, ask:
   ```text
   what command did you use to verify that exit code?
   ```
   *Expected:* Retains context and answers using `get_pod_status` / cgroup exit code.

---

### Section H: Safe Remediation & Auto-Rollback Engine
1. **Propose Remediation (Dry Run):**
   ```python
   from mcp_servers.remediation.server import propose_remediation, apply_remediation
   p = propose_remediation("payment-service", "set_memory_limit", {"memory_mb": 256}, "OOM fix")
   print(p)  # Shows dry_run, risk: "medium", and approval_token
   ```
   Verify Docker memory limit is untouched:
   ```bash
   docker inspect payment-service --format '{{.HostConfig.Memory}}'
   ```
2. **Apply Remediation with Single-Use Token:**
   ```python
   res = apply_remediation(p["proposal_id"], p["approval_token"], approver="sre_lead")
   print(res)  # status: "applied"
   ```
3. **Verify Bad-Fix Automatic Rollback:**
   ```python
   p_bad = propose_remediation("payment-service", "set_memory_limit", {"memory_mb": 32}, "flawed fix")
   res_bad = apply_remediation(p_bad["proposal_id"], p_bad["approval_token"], approver="sre_lead")
   ```
   Inspect `data/audit_log.jsonl`: observe `verification_degraded` followed by `auto_rollback_completed`.
4. **Safety Boundaries:**
   - Parameter tampering: Refused (`parameter_tampering_detected`).
   - Unauthorized approver: Refused (`unauthorized_approver`).
   - Token re-use: Refused (`invalid_or_used_token`).

---

### Section I: Continuous Learning Loop
1. **Draft Runbook:**
   ```bash
   python -m agent.api "chatops learn: service inventory-service experienced redis connection timeout on port 6379 after network blip"
   ```
   *Expected:* Draft created in `data/runbooks/drafts/`. Searching for it in RAG returns 0 results (quarantined).
2. **Approve and Re-Index:**
   ```bash
   python -m agent.api "chatops approve data/runbooks/drafts/<draft_filename>.md"
   ```
   *Expected:* Draft moved to `data/runbooks/` and immediately indexed into Chroma DB.
3. **Run Learning Curve Evaluation:**
   ```bash
   python -m agent.eval.learning_curve
   ```
   *Expected:* `Learning curve evaluation PASSED`.

---

### Section J: Incident Memory & Log Pattern Mining
1. **Run Incident Memory Telemetry Test:**
   ```bash
   python -m agent.eval.eval_incident_memory
   ```
   *Expected:* `4 / 4 PASSED` (Multi-archetype retrieval from 120 recorded live incident snapshots).
2. **Run Unseen Hold-Out Generalisation Test (T9):**
   ```bash
   python agent/eval/eval_incident_memory_generalisation.py
   ```
   *Expected:* `3 / 3 (100.0%)` generalisation accuracy, `0.0%` wrong-type rate, `0/3` leaks across held-out runs.
3. **Run LogHub Drain3 Pattern Mining:**
   ```bash
   python -m agent.eval.eval_loghub
   ```
   *Expected:* 48 structured templates extracted from 2,000 public HDFS log lines in 0.007s.

---

### Section K: Evaluation Artefacts & SVG Charts
1. **Verify Raw Benchmark JSON Files:**
   Check that `agent/eval/results/` contains:
   - `benchmark_2026-11-12.json`
   - `benchmark_variants_2026-11-12.json`
   - `benchmark_2026-11-12_external_ablation.json`
   - `incident_memory_generalisation.json`
   - `loghub_eval.json`
2. **Regenerate All 5 Charts from JSON:**
   ```bash
   python agent/eval/generate_charts.py
   ```
   *Expected:* Successfully regenerates:
   - `charts/accuracy_by_ablation.svg`
   - `charts/accuracy_by_model.svg`
   - `charts/latency_and_cost.svg`
   - `charts/holdout_and_learning_curve.svg`
   - `charts/variants_by_category.svg`

---

### Section L: Demo Rehearsal
Follow the full rehearsal script in [docs/demo_script.md](file:///Users/nikhi/Desktop/Chatops/chatops-agent/docs/demo_script.md).
- Scenario 1: OOM diagnosis & Slack approval.
- Scenario 2: Bad deploy & rollback.
- Scenario 3: Bad-fix auto-rollback verification (`audit_4bc27397d840`).
- Viva Defense: Deliver the dataset statement verbatim.
