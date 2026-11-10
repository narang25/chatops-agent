#!/usr/bin/env python3
"""
Chaos Suite Runner for Automated Incident Collection & Evaluation (Task B19).

Executes unattended chaos testing across scenarios:
  - Supports --repeat N, --seed S, --dry-run
  - Executes failure injection, waits for stabilization, records incident snapshot
  - Restores to healthy between every run
  - Emits one stable JSON line per run to stdout (for benchmark consumption)
  - Appends manifest records to data/incident_logs/chaos_manifest.jsonl
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FAILURES_DIR = REPO_ROOT / "infra" / "failures"
MANIFEST_PATH = REPO_ROOT / "data" / "incident_logs" / "chaos_manifest.jsonl"

# The 10 standard evaluation scenarios
SCENARIO_IDS = [
    "oom-payment-001",
    "badenv-order-001",
    "healthfail-inventory-001",
    "dbtimeout-payment-001",
    "depfail-order-001",
    "cpusat-payment-001",
    "diskfull-inventory-001",
    "nettimeout-order-001",
    "baddeploy-order-001",
    "crashloop-payment-001",
]


def run_scenario(scenario_id: str, dry_run: bool = False) -> dict:
    if dry_run:
        return {
            "status": "injected",
            "scenario_id": scenario_id,
            "service": "simulated-service",
            "failure_type": "simulated",
        }

    cmd = [sys.executable, str(FAILURES_DIR / "run_scenario.py"), "run", scenario_id]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(REPO_ROOT))
    if proc.returncode != 0:
        return {"status": "error", "scenario_id": scenario_id, "error": proc.stderr.strip()}

    try:
        # Find last JSON line from stdout
        for line in reversed(proc.stdout.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                return json.loads(line)
    except Exception:
        pass
    return {"status": "injected", "scenario_id": scenario_id}


def restore_system(dry_run: bool = False):
    if dry_run:
        return
    cmd = [sys.executable, str(FAILURES_DIR / "run_scenario.py"), "restore"]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(REPO_ROOT))
    time.sleep(2.0)


def main():
    parser = argparse.ArgumentParser(description="Chaos Suite Unattended Runner")
    parser.add_argument("--repeat", type=int, default=1, help="Number of times to run each scenario")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for scenario permutation")
    parser.add_argument("--jitter", type=float, default=0.0, help="Max random jitter sleep (seconds) between runs")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying containers")
    parser.add_argument("--include-surprise", action="store_true", help="Include surprise scenarios in the run")
    args = parser.parse_args()

    random.seed(args.seed)

    scenarios = list(SCENARIO_IDS)
    if args.include_surprise:
        scenarios.extend(["surprise_1", "surprise_2"])

    run_plan = []
    for iteration in range(args.repeat):
        shuffled = list(scenarios)
        random.shuffle(shuffled)
        for s in shuffled:
            run_plan.append((iteration + 1, s))

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    from infra.failures.recorder import record_incident_snapshot

    total_runs = len(run_plan)
    for idx, (rep, scenario_id) in enumerate(run_plan, start=1):
        started_at = datetime.now(timezone.utc).isoformat()
        run_id = f"{scenario_id}_r{rep}_{int(time.time())}"

        # 1. Run scenario injection
        res = run_scenario(scenario_id, dry_run=args.dry_run)
        service = res.get("service", "unknown-service")
        failure_type = res.get("failure_type", "unknown")

        if not args.dry_run:
            time.sleep(2.0)

        # 2. Record incident snapshot
        snapshot_dir = None
        if not args.dry_run:
            try:
                snapshot_dir = str(record_incident_snapshot(scenario_id, service, run_id=run_id, minutes=3))
            except Exception as e:
                snapshot_dir = f"recording_error: {e}"

        # 3. Restore to clean state
        restore_system(dry_run=args.dry_run)

        # 4. Manifest record
        manifest_record = {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "service": service,
            "failure_type": failure_type,
            "started_at": started_at,
            "snapshot_dir": snapshot_dir,
            "repetition": rep,
            "run_index": idx,
            "total_runs": total_runs,
        }

        # Stable stdout JSON line for benchmark ingestion
        print(json.dumps(manifest_record), flush=True)

        with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(manifest_record) + "\n")

        if args.jitter > 0:
            time.sleep(random.uniform(0.1, args.jitter))


if __name__ == "__main__":
    main()
