#!/usr/bin/env python3
"""
Failure Scenario: bad_deploy / high_error_rate on order-service.

Simulates a bad deployment by activating an error_rate fault (50% of
non-health requests return HTTP 500). Records a deploy event to
data/deploy_events.jsonl so what_changed can surface it.

Workflow:
1. Verify order-service is healthy. Record pre-deploy error rate baseline.
2. Write a deploy event to data/deploy_events.jsonl.
3. Activate error_rate=0.5 fault via POST /admin/fault.
4. Send requests to confirm the error rate spike.
5. Extract logs and write ground truth metadata.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import httpx

SCENARIO_ID = "baddeploy-order-001"
SERVICE_NAME = "order-service"
CONTAINER_NAME = "order-service"
SERVICE_URL = "http://localhost:8002"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.path.join(REPO_ROOT, "data", "incident_logs")
JSONL_PATH = os.path.join(LOG_DIR, f"{SCENARIO_ID}.jsonl")
META_PATH = os.path.join(LOG_DIR, f"{SCENARIO_ID}.meta.json")
DEPLOY_LOG = os.path.join(REPO_ROOT, "data", "deploy_events.jsonl")


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

    client = httpx.Client(timeout=5.0)

    # 1. Verify health
    print("Step 1: Checking initial health of order-service...")
    try:
        resp = client.get(f"{SERVICE_URL}/health", timeout=3.0)
        print(f"  order-service health: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Warning: could not connect: {e}")

    deploy_ts = datetime.now(timezone.utc).isoformat()
    since_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Write deploy event (what_changed will surface this)
    print("Step 2: Recording deploy event to data/deploy_events.jsonl...")
    os.makedirs(os.path.dirname(DEPLOY_LOG), exist_ok=True)
    deploy_event = {
        "timestamp": deploy_ts,
        "service": SERVICE_NAME,
        "action": "deploy",
        "image": "infra-order-service:bad-v2",
        "trigger": "bad_deploy scenario injection",
        "scenario_id": SCENARIO_ID,
        "description": "Simulated bad deploy: order-service v2 with 50% error rate bug",
    }
    with open(DEPLOY_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(deploy_event) + "\n")
    print(f"  Deploy event written: {deploy_ts}")

    # 3. Activate error_rate fault (50%)
    print("Step 3: Activating error_rate=0.5 fault (50% of requests return 500)...")
    try:
        resp = client.post(f"{SERVICE_URL}/admin/fault", json={"error_rate": 0.5})
        print(f"  Fault response: {resp.text}")
    except Exception as e:
        print(f"  Error activating fault: {e}")
        sys.exit(1)

    time.sleep(1.0)

    # 4. Send requests and count errors
    print("Step 4: Sending requests to verify error rate spike...")
    signals: list[str] = ["fault_error_rate=0.5", "deploy_event_recorded"]
    error_count = 0
    total_requests = 20

    for i in range(total_requests):
        try:
            resp = client.get(f"{SERVICE_URL}/health")
            # Also hit a real endpoint
            resp2 = client.post(
                f"{SERVICE_URL}/orders",
                json={"item": "widget", "quantity": 1, "amount": 9.99},
                timeout=5.0,
            )
            if resp2.status_code == 500:
                error_count += 1
        except Exception:
            error_count += 1

    error_pct = error_count / total_requests * 100
    print(f"  Error rate: {error_count}/{total_requests} = {error_pct:.0f}%")
    signals.append(f"measured_error_rate={error_pct:.0f}pct")
    if error_pct >= 30:
        signals.append("http_error_rate_spike_confirmed")
        signals.append("app_errors_total_spike_after_deploy")

    # 5. Extract logs
    print(f"Step 5: Capturing JSON logs to {JSONL_PATH}...")
    json_lines = extract_json_logs(CONTAINER_NAME, since_ts)
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for line in json_lines:
            f.write(line + "\n")
    print(f"Saved {len(json_lines)} JSON log entries.")

    # 6. Write metadata
    print(f"Step 6: Writing ground truth metadata to {META_PATH}...")
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": SERVICE_NAME,
        "failure_type": "high_error_rate",
        "root_cause": (
            "A simulated bad deploy sets FAULT_ERROR_RATE=0.5 on order-service, "
            "causing 50% of non-health requests to return HTTP 500. "
            "The deploy event is timestamped in data/deploy_events.jsonl "
            "immediately before the error spike."
        ),
        "expected_fix": (
            "Roll back the deployment: POST /admin/fault with {\"error_rate\": 0} "
            "to clear the fault. In production: use blue-green deploys or canary "
            "releases with automated error-rate gates to catch regressions before "
            "full rollout."
        ),
        "signals": signals,
        "deploy_timestamp": deploy_ts,
        "how_to_reproduce": "python infra/failures/run_scenario.py run baddeploy-order-001",
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/run_scenario.py restore")


if __name__ == "__main__":
    main()
