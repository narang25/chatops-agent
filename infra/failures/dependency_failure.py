#!/usr/bin/env python3
"""
Failure Scenario 5: Dependency Failure on order-service.

Workflow:
1. Verify order-service is initially running.
2. Stop payment-service container (simulating downstream dependency failure).
3. Send requests to order-service POST /orders.
4. Observe HTTP 502 Bad Gateway responses and error logs targeting payment-service.
5. Extract JSON logs to data/incident_logs/depfail-order-001.jsonl.
6. Generate ground truth metadata to data/incident_logs/depfail-order-001.meta.json.
7. Print instructions to restore service.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
import httpx

SCENARIO_ID = "depfail-order-001"
SERVICE_NAME = "order-service"
CONTAINER_NAME = "order-service"
DEPENDENCY_CONTAINER = "payment-service"
SERVICE_URL = "http://localhost:8002"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.path.join(REPO_ROOT, "data", "incident_logs")
JSONL_PATH = os.path.join(LOG_DIR, f"{SCENARIO_ID}.jsonl")
META_PATH = os.path.join(LOG_DIR, f"{SCENARIO_ID}.meta.json")


def run_cmd(cmd: list[str]) -> str:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout.strip()


def extract_json_logs(container: str, since_ts: str) -> list[str]:
    raw_logs = run_cmd(["docker", "logs", "--since", since_ts, container])
    valid_lines = []
    for line in raw_logs.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            if "timestamp" in parsed and "level" in parsed:
                valid_lines.append(json.dumps(parsed))
        except Exception:
            continue
    return valid_lines


def main():
    print(f"=== Starting Failure Injection: {SCENARIO_ID} ===")
    os.makedirs(LOG_DIR, exist_ok=True)

    client = httpx.Client(timeout=8.0)

    # 1. Verify health
    print("Step 1: Checking initial health of order-service...")
    try:
        resp = client.get(f"{SERVICE_URL}/health", timeout=3.0)
        if resp.status_code != 200:
            print(f"Warning: order-service returned {resp.status_code}, expected 200")
        else:
            print("Order service is healthy.")
    except Exception as e:
        print(f"Warning: could not connect to order-service: {e}, continuing...")

    since_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Stop dependency container
    print(f"Step 2: Stopping dependency container {DEPENDENCY_CONTAINER}...")
    run_cmd(["docker", "stop", DEPENDENCY_CONTAINER])

    # 3. Observe symptoms: send order requests that require payment-service
    print("Step 3: Sending order requests to order-service (expecting 502)...")
    signals = ["dependency_down=payment-service"]

    for i in range(1, 4):
        try:
            order_resp = client.post(
                f"{SERVICE_URL}/orders",
                json={"item": "widget", "quantity": 1, "amount": 25.0 * i},
            )
            print(f"  Order {i} response: HTTP {order_resp.status_code} - {order_resp.text}")
            if order_resp.status_code == 502:
                signals.append("http_status=502")
                signals.append("connection_refused_payment_service")
        except Exception as e:
            print(f"  Order {i} request error: {e}")

    # 4. Extract logs
    print(f"Step 4: Capturing JSON logs to {JSONL_PATH}...")
    json_lines = extract_json_logs(CONTAINER_NAME, since_ts)
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for line in json_lines:
            f.write(line + "\n")
    print(f"Saved {len(json_lines)} JSON log entries.")

    # 5. Write metadata
    print(f"Step 5: Writing ground truth metadata to {META_PATH}...")
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": SERVICE_NAME,
        "failure_type": "dependency_failure",
        "root_cause": "Downstream dependency payment-service is unreachable (stopped); order-service fails with HTTP 502",
        "expected_fix": "Restart payment-service container: docker start payment-service",
        "signals": list(set(signals)),
        "how_to_reproduce": "python infra/failures/dependency_failure.py"
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/restore.py")


if __name__ == "__main__":
    main()
