#!/usr/bin/env python3
"""
Failure Scenario 3: Health Check Failure on inventory-service.

Workflow:
1. Verify initial health of inventory-service.
2. Inject health_fail fault via POST /admin/fault {"health_fail": true}.
3. Detect symptoms (GET /health returns 500, app_up metric drops to 0, Docker container reports unhealthy).
4. Extract JSON logs to data/incident_logs/healthfail-inventory-001.jsonl.
5. Generate ground truth metadata to data/incident_logs/healthfail-inventory-001.meta.json.
6. Print restore instructions.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
import httpx

SCENARIO_ID = "healthfail-inventory-001"
SERVICE_NAME = "inventory-service"
CONTAINER_NAME = "inventory-service"
SERVICE_URL = "http://localhost:8003"
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
    print("Step 1: Checking initial health of inventory-service...")
    try:
        resp = client.get(f"{SERVICE_URL}/health")
        if resp.status_code != 200:
            print(f"Warning: inventory-service returned {resp.status_code}, continuing anyway...")
        else:
            print("Inventory service is currently healthy.")
    except Exception as e:
        print(f"Warning: could not connect to inventory-service: {e}, continuing...")

    since_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Inject fault
    print("Step 2: Activating health_fail fault toggle via POST /admin/fault...")
    try:
        fault_resp = client.post(f"{SERVICE_URL}/admin/fault", json={"health_fail": True})
        print(f"  Fault response: {fault_resp.text}")
    except Exception as e:
        print(f"Error calling /admin/fault: {e}")
        sys.exit(1)

    # 3. Observe symptoms
    print("Step 3: Checking symptoms (/health endpoint and Docker health status)...")
    signals = ["fault_health_fail=true"]

    try:
        health_check = client.get(f"{SERVICE_URL}/health")
        print(f"  GET /health returned HTTP {health_check.status_code}: {health_check.text}")
        if health_check.status_code == 500:
            signals.append("http_status=500")
            signals.append("status=unhealthy")
    except Exception as e:
        print(f"  Health request error: {e}")

    # Wait briefly for Docker health check cycles
    print("  Waiting 10s for Docker health checks to record failures...")
    time.sleep(10.0)

    info = inspect_container(CONTAINER_NAME)
    health_info = info.get("State", {}).get("Health", {})
    health_status = health_info.get("Status", "unknown")
    print(f"  Docker inspect health status: {health_status}")
    if health_status:
        signals.append(f"docker_health={health_status}")

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
        "failure_type": "health_check_failure",
        "root_cause": "Health check toggle health_fail set to true via /admin/fault; GET /health returns 500 Internal Server Error",
        "expected_fix": "Reset fault toggle health_fail to false via POST /admin/fault",
        "signals": signals,
        "how_to_reproduce": "python infra/failures/health_fail.py"
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/restore.py")


if __name__ == "__main__":
    main()
