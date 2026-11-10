#!/usr/bin/env python3
"""
Surprise Failure Scenario 2: Connection Pool Exhaustion on payment-service.

Note:
- Has NO runbook in data/runbooks/
- failure_type is NOT one of the standard 10 (agent should report failure_type: unknown)
- Ground truth is stored in infra/failures/ground_truth_secret/ (gitignored)
"""

import json
import os
import subprocess
import sys
import threading
import time
import httpx

SCENARIO_ID = "surprise_2"
SERVICE_NAME = "payment-service"
SERVICE_URL = "http://localhost:8001"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SECRET_GT_DIR = os.path.join(REPO_ROOT, "infra", "failures", "ground_truth_secret")
META_PATH = os.path.join(SECRET_GT_DIR, f"{SCENARIO_ID}.meta.json")


def main():
    print(f"=== Starting Failure Injection: {SCENARIO_ID} (Surprise Scenario 2) ===")
    os.makedirs(SECRET_GT_DIR, exist_ok=True)

    print("Step 1: Inundating payment-service with 150 concurrent connections to exhaust pool...")

    def hammer():
        try:
            with httpx.Client(timeout=1.0) as client:
                client.post(f"{SERVICE_URL}/pay", json={"amount": 1.0})
        except Exception:
            pass

    threads = [threading.Thread(target=hammer) for _ in range(150)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=0.1)

    # Save ground truth secretly
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": SERVICE_NAME,
        "failure_type": "unknown",
        "actual_issue": "connection_pool_exhaustion",
        "root_cause": "Burst of 150 concurrent payment transactions exhausted Postgres connection limit",
        "expected_fix": "Increase max_connections in postgresql.conf or implement client-side connection pooling",
        "signals": ["too_many_clients_already", "remaining_connection_slots_reserved"],
        "has_runbook": False,
        "how_to_reproduce": "python infra/failures/surprise_2.py",
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete (Surprise 2) ===")
    print("Restore command: python infra/failures/restore.py")


if __name__ == "__main__":
    main()
