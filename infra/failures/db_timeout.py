#!/usr/bin/env python3
"""
Failure Scenario 4: Database Timeout on payment-service.

Workflow:
1. Verify payment-service is healthy.
2. Activate slow_db fault toggle via POST /admin/fault {"slow_db": true}.
3. Send requests to POST /pay and observe elevated latency and timeouts.
4. Extract JSON logs to data/incident_logs/dbtimeout-payment-001.jsonl.
5. Generate ground truth metadata to data/incident_logs/dbtimeout-payment-001.meta.json.
6. Print instructions to restore service.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
import httpx

SCENARIO_ID = "dbtimeout-payment-001"
SERVICE_NAME = "payment-service"
CONTAINER_NAME = "payment-service"
SERVICE_URL = "http://localhost:8001"
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

    client = httpx.Client(timeout=10.0)

    # 1. Verify health
    print("Step 1: Checking initial health of payment-service...")
    try:
        resp = client.get(f"{SERVICE_URL}/health", timeout=3.0)
        if resp.status_code != 200:
            print(f"Warning: payment-service returned {resp.status_code}, expected 200")
        else:
            print("Payment service is healthy.")
    except Exception as e:
        print(f"Warning: could not connect to payment-service: {e}, continuing...")

    since_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Inject fault
    print("Step 2: Activating slow_db fault toggle via POST /admin/fault...")
    try:
        fault_resp = client.post(f"{SERVICE_URL}/admin/fault", json={"slow_db": True})
        print(f"  Fault response: {fault_resp.text}")
    except Exception as e:
        print(f"Error calling /admin/fault: {e}")
        sys.exit(1)

    # 3. Observe symptoms: send payment requests that will experience delayed DB queries
    print("Step 3: Sending payment requests to observe DB latency...")
    signals = ["fault_slow_db=true"]
    latencies = []

    for i in range(1, 4):
        try:
            t0 = time.perf_counter()
            pay_resp = client.post(f"{SERVICE_URL}/pay", json={"amount": 10.0 * i})
            latency = time.perf_counter() - t0
            latencies.append(latency)
            print(f"  Payment {i} completed in {latency:.2f}s (HTTP {pay_resp.status_code})")
        except Exception as e:
            print(f"  Payment {i} failed/timed out: {e}")
            signals.append("request_timeout")

    if any(l >= 3.0 for l in latencies):
        signals.append("latency_exceeded_3s")
        signals.append("db_query_delay=3000ms")

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
        "failure_type": "db_timeout",
        "root_cause": "Postgres database query latency artificial delay (slow_db=true) causing timeouts and degraded throughput",
        "expected_fix": "Reset fault toggle slow_db to false via POST /admin/fault, or inspect Postgres lock contention",
        "signals": signals,
        "how_to_reproduce": "python infra/failures/db_timeout.py"
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/restore.py")


if __name__ == "__main__":
    main()
