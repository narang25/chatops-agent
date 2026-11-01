#!/usr/bin/env python3
"""
Surprise Failure Scenario 1: Wrong Database Password on order-service.

Note:
- Has NO runbook in data/runbooks/
- failure_type is NOT one of the 10 standard types (agent should report failure_type: unknown)
- Ground truth is stored in infra/failures/ground_truth_secret/ (gitignored)
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

SCENARIO_ID = "surprise_1"
SERVICE_NAME = "order-service"
CONTAINER_NAME = "order-service"
SERVICE_URL = "http://localhost:8002"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SECRET_GT_DIR = os.path.join(REPO_ROOT, "infra", "failures", "ground_truth_secret")
META_PATH = os.path.join(SECRET_GT_DIR, f"{SCENARIO_ID}.meta.json")


def run_cmd(cmd: list[str]) -> str:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout.strip()


def main():
    print(f"=== Starting Failure Injection: {SCENARIO_ID} (Surprise Scenario 1) ===")
    os.makedirs(SECRET_GT_DIR, exist_ok=True)

    # Inject invalid database password by starting order-service with wrong password
    print("Step 1: Starting order-service instance with incorrect DATABASE_URL credentials...")
    run_cmd(["docker", "stop", "order-service"])
    run_cmd(["docker", "rm", "-f", "order-service-surprise1"])

    run_cmd([
        "docker", "run", "-d",
        "--name", "order-service-surprise1",
        "--network", "infra_default",
        "-e", "SERVICE_NAME=order-service",
        "-e", "DATABASE_URL=postgresql://chatops:WRONG_PASSWORD_XYZ@postgres:5432/chatops",
        "-e", "PAYMENT_SERVICE_URL=http://payment-service:8000",
        "infra-order-service",
    ])

    time.sleep(2.0)

    # Save ground truth secretly
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": SERVICE_NAME,
        "failure_type": "unknown",
        "actual_issue": "invalid_database_password",
        "root_cause": "DATABASE_URL configured with invalid password 'WRONG_PASSWORD_XYZ', causing authentication failure",
        "expected_fix": "Provide correct Postgres password in DATABASE_URL environment variable",
        "signals": ["password_authentication_failed_for_user_chatops", "database_connection_refused"],
        "has_runbook": False,
        "how_to_reproduce": "python infra/failures/surprise_1.py",
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete (Surprise 1) ===")
    print("Restore command: python infra/failures/restore.py")


if __name__ == "__main__":
    main()
