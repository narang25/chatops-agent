#!/usr/bin/env python3
"""
Unified Failure Scenario Runner for ChatOps Benchmark & Local Testing.

Interface:
    python infra/failures/run_scenario.py list
        Outputs JSON array of registered scenario IDs.

    python infra/failures/run_scenario.py run <scenario_id>
        Executes failure injection without restoring, waits for symptoms,
        and outputs a single JSON line:
        {"status": "injected", "scenario_id": "...", "service": "...", "failure_type": "..."}

    python infra/failures/run_scenario.py restore
        Restores all containers, memory limits, and fault toggles to healthy.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

FAILURES_DIR = Path(__file__).resolve().parent
REPO_ROOT = FAILURES_DIR.parent.parent

SCENARIOS = {
    "oom-payment-001": {
        "script": "oom.py",
        "service": "payment-service",
        "failure_type": "out_of_memory",
        "description": "Payment service memory leak leading to OOM crash",
    },
    "badenv-order-001": {
        "script": "bad_env.py",
        "service": "order-service",
        "failure_type": "bad_config",
        "description": "Order service missing PAYMENT_SERVICE_URL causing crash loop",
    },
    "healthfail-inventory-001": {
        "script": "health_fail.py",
        "service": "inventory-service",
        "failure_type": "health_check_failure",
        "description": "Inventory service health check failure flag active",
    },
    "dbtimeout-payment-001": {
        "script": "db_timeout.py",
        "service": "payment-service",
        "failure_type": "db_timeout",
        "description": "Payment service slow DB query delay causing timeout",
    },
    "depfail-order-001": {
        "script": "dependency_failure.py",
        "service": "order-service",
        "failure_type": "dependency_failure",
        "description": "Downstream payment-service stopped causing 502 in order-service",
    },
    "cpusat-payment-001": {
        "script": "cpu_saturation.py",
        "service": "payment-service",
        "failure_type": "cpu_saturation",
        "description": "Payment service intensive compute loop saturating CPU",
    },
}


def cmd_list():
    scenario_list = [
        {
            "scenario_id": sid,
            "service": info["service"],
            "failure_type": info["failure_type"],
            "description": info["description"],
        }
        for sid, info in SCENARIOS.items()
    ]
    print(json.dumps(scenario_list, indent=2))


def cmd_run(scenario_id: str):
    if scenario_id not in SCENARIOS:
        print(
            json.dumps(
                {
                    "error": f"Unknown scenario_id: {scenario_id}",
                    "available_scenarios": list(SCENARIOS.keys()),
                }
            )
        )
        sys.exit(1)

    info = SCENARIOS[scenario_id]
    script_path = FAILURES_DIR / info["script"]

    if not script_path.exists():
        print(json.dumps({"error": f"Script not found: {script_path}"}))
        sys.exit(1)

    # Run injection script
    proc = subprocess.run([sys.executable, str(script_path)], cwd=REPO_ROOT)
    if proc.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "scenario_id": scenario_id,
                    "returncode": proc.returncode,
                }
            )
        )
        sys.exit(proc.returncode)

    # Output stable JSON summary for benchmark ingestion
    result = {
        "status": "injected",
        "scenario_id": scenario_id,
        "service": info["service"],
        "failure_type": info["failure_type"],
    }
    print(json.dumps(result))


def cmd_restore():
    restore_script = FAILURES_DIR / "restore.py"
    if not restore_script.exists():
        print(json.dumps({"error": f"Restore script not found: {restore_script}"}))
        sys.exit(1)

    proc = subprocess.run([sys.executable, str(restore_script)], cwd=REPO_ROOT)
    sys.exit(proc.returncode)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1].lower()
    if action == "list":
        cmd_list()
    elif action == "run":
        if len(sys.argv) < 3:
            print("Error: scenario_id required for 'run' command.")
            print("Usage: python infra/failures/run_scenario.py run <scenario_id>")
            sys.exit(1)
        cmd_run(sys.argv[2])
    elif action == "restore":
        cmd_restore()
    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
