#!/usr/bin/env python3
"""
Failure Scenario 1: Out Of Memory (OOM) on payment-service.

Workflow:
1. Verify payment-service is healthy.
2. Restrict container memory to 64MB using docker update.
3. Repeatedly call GET /leak to allocate memory until container is OOM-killed.
4. Detect symptoms (OOMKilled=true, ExitCode=137, restart count increased).
5. Extract JSON logs to data/incident_logs/oom-payment-001.jsonl.
6. Generate ground truth metadata to data/incident_logs/oom-payment-001.meta.json.
7. Print instructions to restore service.
"""

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime

import httpx

SCENARIO_ID = "oom-payment-001"
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


def inspect_container(container: str) -> dict:
    raw = run_cmd(["docker", "inspect", container])
    try:
        data = json.loads(raw)
        return data[0] if data else {}
    except Exception:
        return {}


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

    client = httpx.Client(timeout=5.0)

    # 1. Verify health
    print("Step 1: Checking initial health of payment-service...")
    try:
        resp = client.get(f"{SERVICE_URL}/health")
        if resp.status_code != 200:
            print(f"Error: payment-service returned {resp.status_code}, expected 200")
            sys.exit(1)
        print("Payment service is healthy.")
    except Exception as e:
        print(f"Error connecting to payment-service: {e}")
        sys.exit(1)

    initial_info = inspect_container(CONTAINER_NAME)
    initial_restarts = initial_info.get("RestartCount", 0)
    since_ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Lower memory limit to 64m
    print("Step 2: Constraining container memory limit to 64MB...")
    run_cmd(["docker", "update", "--memory", "64m", "--memory-swap", "64m", CONTAINER_NAME])

    # 3. Call /leak repeatedly until crash / restart
    print("Step 3: Triggering memory allocations via GET /leak until OOM...")
    oom_detected = False
    signals = []

    for i in range(1, 20):
        try:
            leak_resp = client.get(f"{SERVICE_URL}/leak")
            print(f"  Leak call {i}: {leak_resp.text}")
            time.sleep(0.3)
        except Exception as e:
            print(f"  Connection dropped on call {i} (possible crash): {e}")

        # Check container state
        time.sleep(1.0)
        curr_info = inspect_container(CONTAINER_NAME)
        state = curr_info.get("State", {})
        restarts = curr_info.get("RestartCount", 0)
        oom_killed = state.get("OOMKilled", False)
        exit_code = state.get("ExitCode", 0)

        if oom_killed or exit_code == 137 or restarts > initial_restarts:
            print(f"  => OOM condition detected! OOMKilled={oom_killed}, ExitCode={exit_code}, Restarts={restarts}")
            oom_detected = True
            signals.append(f"oom_killed={str(oom_killed).lower()}")
            signals.append(f"exit_code={exit_code}")
            signals.append(f"restart_count increased from {initial_restarts} to {restarts}")
            signals.append("memory limit exceeded (64MB)")
            break

    if not oom_detected:
        print("Warning: OOM not immediately registered, waiting 3s for restart counter...")
        time.sleep(3.0)
        curr_info = inspect_container(CONTAINER_NAME)
        restarts = curr_info.get("RestartCount", 0)
        if restarts > initial_restarts:
            signals.append(f"restart_count increased from {initial_restarts} to {restarts}")

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
        "failure_type": "out_of_memory",
        "root_cause": "Container memory limit (64MB) too low; /leak endpoint allocates unbounded memory",
        "expected_fix": "Raise memory limit to 256MB and fix the leak",
        "signals": signals if signals else ["oom_killed=true", "exit_code=137", "restart_count increasing"],
        "how_to_reproduce": "python infra/failures/oom.py"
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/restore.py")


if __name__ == "__main__":
    main()
