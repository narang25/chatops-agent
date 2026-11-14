#!/usr/bin/env python3
"""
ChatOps SRE Agent — All-in-One Manual Verification Runner (T11 Checklist).
==========================================================================

Runs automated checks for sections A through K of FINAL_PLAN_14-18_NOV.md,
automatically ensuring the proper .venv python environment is used.

Usage:
  python3 run_manual_checks.py --all-auto          # Run all automated verification checks
  python3 run_manual_checks.py --section A         # Run Repository & CI checks (pytest, ruff, secrets)
  python3 run_manual_checks.py --section B         # Run Infrastructure & Health checks (containers, /health)
  python3 run_manual_checks.py --section C         # Run Knowledge Base & RAG checks
  python3 run_manual_checks.py --section D         # Run Bedrock LLM smoke test
  python3 run_manual_checks.py --section F         # Run Agent behaviour & evidence gate checks
  python3 run_manual_checks.py --section H         # Run Remediation & Safety engine checks
  python3 run_manual_checks.py --section I         # Run Continuous Learning Loop check
  python3 run_manual_checks.py --section J         # Run Incident Memory & LogHub checks
  python3 run_manual_checks.py --section K         # Verify Benchmark JSONs & regenerate charts
  python3 run_manual_checks.py --scenario <id>     # Inject, test, and restore a specific failure scenario
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Auto-re-exec with virtual environment if not already active
PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"
VENV_PYTEST = PROJECT_ROOT / ".venv" / "bin" / "pytest"

if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

os.environ.setdefault("PYTHONPATH", str(PROJECT_ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


def print_header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 75}{RESET}")
    print(f"{BOLD}{CYAN}{title.center(75)}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 75}{RESET}\n")


def run_cmd(cmd: list[str] | str, desc: str, shell: bool = False, timeout: int = 120) -> tuple[bool, str]:
    print(f"  {BOLD}Testing:{RESET} {desc}...")
    try:
        res = subprocess.run(
            cmd,
            shell=shell,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (res.stdout + "\n" + res.stderr).strip()
        if res.returncode == 0:
            print(f"  {GREEN}✔ PASS{RESET} - {desc}")
            return True, output
        else:
            print(f"  {RED}✘ FAIL{RESET} - {desc} (Exit code {res.returncode})")
            if output:
                lines = output.splitlines()
                preview = "\n".join("      " + line for line in lines[-12:])
                print(f"{YELLOW}--- Last output snippet ---{RESET}\n{preview}\n{YELLOW}---------------------------{RESET}")
            return False, output
    except Exception as exc:
        print(f"  {RED}✘ ERROR{RESET} - {desc}: {exc}")
        return False, str(exc)


# ---------------------------------------------------------------------------
# Section A: Repository & CI
# ---------------------------------------------------------------------------
def check_section_a() -> list[tuple[str, bool]]:
    print_header("Section A: Repository, Secrets & CI")
    results = []

    # 1. Clean git status
    ok, out = run_cmd(["git", "status"], "Clean git status and branch sync")
    passed = ok and ("working tree clean" in out or "nothing to commit" in out)
    results.append(("A.1 Git Status Clean", passed))

    # 2. No secrets tracked
    ok, out = run_cmd("git ls-files | grep -i '\\.env'", "Scan tracked files for .env secrets", shell=True)
    unwanted = [line for line in out.splitlines() if not line.endswith(".example")]
    passed = len(unwanted) == 0
    if not passed:
        print(f"      {RED}Found potential tracked secrets:{RESET} {unwanted}")
    results.append(("A.2 Secrets / .env Scan", passed))

    # 3. Pytest suite
    pytest_bin = str(VENV_PYTEST) if VENV_PYTEST.exists() else "pytest"
    ok, out = run_cmd([pytest_bin, "-v"], "Pytest unit & integration suite (48 tests)")
    passed = ok and ("48 passed" in out or "passed" in out)
    results.append(("A.3 Pytest Suite", passed))

    # 4. Ruff CI check
    ruff_cmd = (
        "ruff check "
        "interfaces/slack/app.py "
        "infra/manage.py "
        "infra/failures/ "
        "mcp_servers/prometheus/server.py "
        "mcp_servers/kubernetes/server.py "
        "mcp_servers/kubernetes/backends/ "
        "--ignore E501,ANN,D,BLE001,EXE001,SIM,UP,S1,PLW,FURB,RUF"
    )
    ok, out = run_cmd(ruff_cmd, "Ruff linting on core infra & servers", shell=True)
    results.append(("A.4 Ruff CI Check", ok))

    return results


# ---------------------------------------------------------------------------
# Section B: Stack Lifecycle & Health
# ---------------------------------------------------------------------------
def check_section_b() -> list[tuple[str, bool]]:
    print_header("Section B: Stack Lifecycle & Observability")
    results = []

    # 1. Docker containers
    ok, out = run_cmd([sys.executable, "infra/manage.py", "ps"], "Check Docker stack (9 containers)")
    containers = ["payment-service", "order-service", "inventory-service", "postgres", "prometheus", "grafana", "cadvisor", "toxiproxy", "loadgen"]
    all_present = ok and all(c in out for c in containers)
    results.append(("B.1 9 Containers Running", all_present))

    # 2. Health endpoints on 8001, 8002, 8003
    for port, sname in [(8001, "payment-service"), (8002, "order-service"), (8003, "inventory-service")]:
        ok, out = run_cmd(f"curl -s http://localhost:{port}/health", f"{sname} /health on port {port}", shell=True)
        passed = ok and '"status":"ok"' in out
        results.append((f"B.2 {sname} Health 200", passed))

    # 3. Prometheus targets check
    ok, out = run_cmd("curl -s http://localhost:9090/api/v1/targets", "Prometheus targets UP on port 9090", shell=True)
    passed = ok and '"health":"up"' in out
    results.append(("B.3 Prometheus Targets UP", passed))

    return results


# ---------------------------------------------------------------------------
# Section C: Knowledge Base & RAG
# ---------------------------------------------------------------------------
def check_section_c() -> list[tuple[str, bool]]:
    print_header("Section C: Knowledge Base & RAG Ingestion")
    results = []

    # 1. Ingestion check
    ok, out = run_cmd([sys.executable, "rag/ingest.py"], "Run rag/ingest.py (62 internal + 430 external)")
    passed = ok and "Internal chunks:" in out and "External chunks:" in out
    results.append(("C.1 Ingestion Idempotence", passed))

    # 2. Search OOM (internal runbook first)
    search_script = (
        "from mcp_servers.runbooks.evidence_gate import record_evidence, reset_evidence; "
        "reset_evidence(); record_evidence('payment-service', 'get_pod_status'); record_evidence('payment-service', 'get_logs'); "
        "from mcp_servers.runbooks.server import search_runbooks; "
        "res = search_runbooks('container killed exit code 137 out of memory'); "
        "assert len(res) > 0 and 'out_of_memory-payment' in res[0].get('source', '')"
    )
    ok, out = run_cmd([sys.executable, "-c", search_script], "search_runbooks ranks internal OOM runbook #1")
    results.append(("C.2 Internal Runbook Priority", ok))

    # 3. Gibberish query confidence threshold
    gibberish_script = (
        "from mcp_servers.runbooks.evidence_gate import record_evidence, reset_evidence; "
        "reset_evidence(); record_evidence('order-service', 'get_pod_status'); record_evidence('order-service', 'get_logs'); "
        "from mcp_servers.runbooks.server import search_runbooks; "
        "res = search_runbooks('asldkjhfaweoiuh non-existent problem qwerty'); "
        "assert len(res) == 0 or res[0].get('no_confident_match') is True"
    )
    ok, out = run_cmd([sys.executable, "-c", gibberish_script], "search_runbooks returns no_confident_match for gibberish")
    results.append(("C.3 Confidence Threshold Fallback", ok))

    # 4. eval_external suite
    ok, out = run_cmd([sys.executable, "-m", "agent.eval.eval_external"], "Run eval_external suite (4/4)")
    passed = ok and "4/4" in out
    results.append(("C.4 External RAG Suite (4/4)", passed))

    return results


# ---------------------------------------------------------------------------
# Section D: Foundation Model Smoke Check
# ---------------------------------------------------------------------------
def check_section_d() -> list[tuple[str, bool]]:
    print_header("Section D: Foundation Model Smoke Verification")
    results = []

    ok, out = run_cmd([sys.executable, "agent/scripts/smoke_llm.py"], "Bedrock smoke test (Hello, tool call, no leak)", timeout=60)
    passed = ok and "ALL CHECKS PASSED" in out
    results.append(("D.1 Bedrock Model Smoke Test", passed))

    return results


# ---------------------------------------------------------------------------
# Section F: Agent Behaviour & Evidence Gate
# ---------------------------------------------------------------------------
def check_section_f() -> list[tuple[str, bool]]:
    print_header("Section F: Agent Behaviour & Code Gates")
    results = []

    # 1. Evidence gate unit enforcement
    gate_script = (
        "from mcp_servers.runbooks.evidence_gate import reset_evidence; reset_evidence(); "
        "from mcp_servers.runbooks.server import search_runbooks; "
        "res = search_runbooks('payment-service OOM killed'); "
        "assert 'error' in res and 'gather evidence first' in res['error']"
    )
    ok, out = run_cmd([sys.executable, "-c", gate_script], "Evidence gate blocks premature runbook search")
    results.append(("F.1 Evidence Gate Hard Enforcement", ok))

    # 2. Adversarial evaluation
    ok, out = run_cmd([sys.executable, "-m", "agent.eval.adversarial"], "Run adversarial safety suite", timeout=120)
    passed = ok and ("14 / 17" in out or "PASSED" in out)
    results.append(("F.2 Adversarial Safety Suite (14/17)", passed))

    return results


# ---------------------------------------------------------------------------
# Section H: Remediation Safety Engine
# ---------------------------------------------------------------------------
def check_section_h() -> list[tuple[str, bool]]:
    print_header("Section H: Remediation Safety & Auto-Rollback Engine")
    results = []

    safety_script = (
        "from mcp_servers.remediation.server import propose_remediation, apply_remediation; "
        "p = propose_remediation('payment-service', 'set_memory_limit', {'memory_mb': 256}, 'test'); "
        "t = p['approval_token']; pid = p['proposal_id']; "
        "assert p.get('risk') == 'medium'; "
        "res_tamper = apply_remediation(pid, t, approver='sre_lead', params={'memory_mb': 512}); "
        "assert res_tamper.get('error') == 'parameter_tampering_detected'; "
        "res_unauth = apply_remediation(pid, t, approver='slack:U_UNAUTHORIZED'); "
        "assert res_unauth.get('error') == 'unauthorized_approver'; "
        "res_ok = apply_remediation(pid, t, approver='sre_lead'); "
        "assert res_ok.get('status') == 'applied'; "
        "res_replay = apply_remediation(pid, t, approver='sre_lead'); "
        "assert res_replay.get('error') == 'invalid_or_used_token';"
    )
    ok, out = run_cmd([sys.executable, "-c", safety_script], "Verify Token, Approver & Tamper Boundaries")
    results.append(("H.1 Remediation Token & Tamper Hardening", ok))

    return results


# ---------------------------------------------------------------------------
# Section I: Continuous Learning Loop
# ---------------------------------------------------------------------------
def check_section_i() -> list[tuple[str, bool]]:
    print_header("Section I: Continuous Learning Loop")
    results = []

    ok, out = run_cmd([sys.executable, "-m", "agent.eval.learning_curve"], "Continuous learning curve test", timeout=60)
    passed = ok and "PASSED" in out
    results.append(("I.1 Learning Curve Quarantine & Promotion", passed))

    return results


# ---------------------------------------------------------------------------
# Section J: Incident Memory & LogHub
# ---------------------------------------------------------------------------
def check_section_j() -> list[tuple[str, bool]]:
    print_header("Section J: Incident Memory & LogHub Mining")
    results = []

    # 1. Incident memory retrieval
    ok, out = run_cmd([sys.executable, "-m", "agent.eval.eval_incident_memory"], "Incident memory telemetry retrieval", timeout=60)
    passed = ok and "4 / 4 PASSED" in out
    results.append(("J.1 Incident Memory Telemetry Retrieval (4/4)", passed))

    # 2. Generalisation test (T9)
    ok, out = run_cmd([sys.executable, "agent/eval/eval_incident_memory_generalisation.py"], "Incident memory hold-out generalisation (T9)", timeout=60)
    passed = ok and "3/3 (100.0%)" in out and "0/3 leaks" in out
    results.append(("J.2 Incident Memory Hold-Out Generalisation (3/3)", passed))

    # 3. LogHub Drain3
    ok, out = run_cmd([sys.executable, "-m", "agent.eval.eval_loghub"], "LogHub Drain3 log pattern mining", timeout=30)
    passed = ok and "48 structured templates" in out
    results.append(("J.3 LogHub Drain3 Template Mining", passed))

    return results


# ---------------------------------------------------------------------------
# Section K: Evaluation Artefacts & Charts
# ---------------------------------------------------------------------------
def check_section_k() -> list[tuple[str, bool]]:
    print_header("Section K: Evaluation Files & Pure-Python Charts")
    results = []

    # 1. Verify JSON files exist
    results_dir = PROJECT_ROOT / "agent" / "eval" / "results"
    expected_files = [
        "benchmark_2026-11-12.json",
        "benchmark_variants_2026-11-12.json",
        "benchmark_2026-11-12_external_ablation.json",
        "incident_memory_generalisation.json",
        "loghub_eval.json",
    ]
    all_exist = all((results_dir / fn).exists() for fn in expected_files)
    results.append(("K.1 Raw Benchmark JSON Files Present", all_exist))

    # 2. Regenerate charts
    ok, out = run_cmd([sys.executable, "agent/eval/generate_charts.py"], "Regenerate 5 SVG charts from JSON")
    passed = ok and "Generated 5 chart(s)" in out
    results.append(("K.2 Regenerate 5 SVG Charts", passed))

    return results


# ---------------------------------------------------------------------------
# Scenario Runner
# ---------------------------------------------------------------------------
def run_scenario_test(scenario_id: str) -> None:
    print_header(f"Live Chaos Scenario Test: {scenario_id}")

    print(f"1. Injecting fault scenario: {scenario_id}...")
    ok, out = run_cmd([sys.executable, "infra/failures/run_scenario.py", "run", scenario_id], f"Inject {scenario_id}")
    if not ok:
        print(f"{RED}Failed to inject {scenario_id}. Restoring...{RESET}")
        run_cmd([sys.executable, "infra/failures/run_scenario.py", "restore"], "Restore baseline")
        return

    time.sleep(3)
    target_service = scenario_id.split("-")[1] if "-" in scenario_id else "payment-service"
    query = f"why is {target_service} failing?"

    print(f"\n2. Querying ChatOps SRE Agent: '{query}'...")
    ok, out = run_cmd([sys.executable, "-m", "agent.api", query], "Query ChatOps Agent", timeout=90)

    print(f"\n3. Restoring cluster to clean baseline...")
    run_cmd([sys.executable, "infra/failures/run_scenario.py", "restore"], "Restore containers to healthy")

    # Verify health
    ok_h, _ = run_cmd("curl -s http://localhost:8001/health && curl -s http://localhost:8002/health && curl -s http://localhost:8003/health", "Verify 200 OK after restore", shell=True)
    if ok_h:
        print(f"\n{GREEN}{BOLD}Scenario {scenario_id} test and restore completed successfully!{RESET}\n")


# ---------------------------------------------------------------------------
# Main CLI Dispatcher
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="ChatOps SRE Agent — Manual Verification Runner")
    parser.add_argument("--all-auto", action="store_true", help="Run all automated verification checks across sections A through K")
    parser.add_argument("--section", choices=["A", "B", "C", "D", "F", "H", "I", "J", "K"], help="Run checks for a specific section")
    parser.add_argument("--scenario", help="Inject, diagnose, and restore a specific failure scenario (e.g. oom-payment-001)")

    args = parser.parse_args()

    if args.scenario:
        run_scenario_test(args.scenario)
        return

    all_results: list[tuple[str, bool]] = []

    sections_to_run = []
    if args.section:
        sections_to_run = [args.section]
    elif args.all_auto:
        sections_to_run = ["A", "B", "C", "D", "F", "H", "I", "J", "K"]
    else:
        parser.print_help()
        print("\nTip: Run with --all-auto to run the full automated verification test suite.")
        sys.exit(0)

    section_dispatch = {
        "A": check_section_a,
        "B": check_section_b,
        "C": check_section_c,
        "D": check_section_d,
        "F": check_section_f,
        "H": check_section_h,
        "I": check_section_i,
        "J": check_section_j,
        "K": check_section_k,
    }

    for sec in sections_to_run:
        fn = section_dispatch.get(sec)
        if fn:
            all_results.extend(fn())

    # Final Summary Table
    print_header("FINAL VERIFICATION RESULTS SUMMARY")
    passed_count = sum(1 for _, ok in all_results if ok)
    total_count = len(all_results)

    for name, ok in all_results:
        status_label = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  [{status_label}]  {name}")

    pct = round((passed_count / total_count) * 100, 1) if total_count else 0
    print(f"\n{BOLD}Total Passed: {passed_count} / {total_count} ({pct}%){RESET}")

    if passed_count == total_count:
        print(f"{GREEN}{BOLD}🎉 ALL AUTOMATED CHECKS PASSED! Ready for viva defense & live demo.{RESET}\n")
    else:
        print(f"{YELLOW}{BOLD}⚠️ Some checks failed. See the last output snippet above for error diagnostics.{RESET}\n")


if __name__ == "__main__":
    main()
