#!/usr/bin/env python3
"""
Failure Scenario 6: CPU Saturation on payment-service.

Workflow:
1. Verify payment-service is initially responsive.
2. Trigger multiple intensive compute cycles via GET /burn?duration_ms=1200.
3. Observe symptoms (high CPU utilization in cAdvisor, latency spikes on standard endpoints).
4. Extract JSON logs to data/incident_logs/cpusat-payment-001.jsonl.
5. Generate ground truth metadata to data/incident_logs/cpusat-payment-001.meta.json.
6. Print instructions to restore service.
"""

import json
import os
import subprocess
import time
from datetime import UTC, datetime

import httpx

SCENARIO_ID = "cpusat-payment-001"
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

    client = httpx.Client(timeout=15.0)

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

    since_ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Trigger CPU burn loops
    print("Step 2: Triggering CPU saturation cycles via /burn...")
    signals = ["cpu_saturation_active", "cpu_limit=0.5_cpus"]

    for i in range(1, 4):
        try:
            t0 = time.perf_counter()
            burn_resp = client.get(f"{SERVICE_URL}/burn?duration_ms=1000")
            elapsed = time.perf_counter() - t0
            print(f"  Burn cycle {i} completed in {elapsed:.2f}s: {burn_resp.text}")
        except Exception as e:
            print(f"  Burn cycle {i} error: {e}")

    # Check concurrent latency
    try:
        t0 = time.perf_counter()
        client.get(f"{SERVICE_URL}/health")
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"  Concurrent health check latency: {latency_ms:.1f}ms")
        signals.append(f"health_check_latency_ms={round(latency_ms, 1)}")
    except Exception as e:
        print(f"  Health check during saturation failed: {e}")

    # 4. Extract logs
    print(f"Step 4: Capturing JSON logs to {JSONL_PATH}...")
    json_lines = extract_json_logs(CONTAINER_NAME, since_ts)
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        f.writelines(line + "\n" for line in json_lines)
    print(f"Saved {len(json_lines)} JSON log entries.")

    # 5. Write metadata
    print(f"Step 5: Writing ground truth metadata to {META_PATH}...")
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": SERVICE_NAME,
        "failure_type": "cpu_saturation",
        "root_cause": "High compute workload (burn cycles) saturating allocated 0.5 CPU container quota",
        "expected_fix": "Increase container CPU limit in compose, or optimize heavy compute routines",
        "signals": signals,
        "how_to_reproduce": "python infra/failures/cpu_saturation.py"
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/restore.py")


if __name__ == "__main__":
    main()
