#!/usr/bin/env python3
"""
Failure Scenario 2: Misconfiguration / Bad Environment on order-service.

Workflow:
1. Verify initial health of order-service.
2. Stop the running order-service container.
3. Start a container instance missing the required PAYMENT_SERVICE_URL environment variable.
4. Detect symptoms (CRITICAL log emitted on startup, exit code 1, crash).
5. Extract JSON logs to data/incident_logs/badenv-order-001.jsonl.
6. Generate ground truth metadata to data/incident_logs/badenv-order-001.meta.json.
7. Print restore instructions.
"""

import json
import os
import subprocess
import time

import httpx

SCENARIO_ID = "badenv-order-001"
SERVICE_NAME = "order-service"
BROKEN_CONTAINER = "order-service-badenv"
SERVICE_URL = "http://localhost:8002"
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


def extract_json_logs(container: str) -> list[str]:
    raw_logs = run_cmd(["docker", "logs", container])
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
        resp = client.get(f"{SERVICE_URL}/health")
        if resp.status_code != 200:
            print(f"Warning: order-service returned {resp.status_code}, continuing anyway...")
        else:
            print("Order service is healthy.")
    except Exception as e:
        print(f"Warning: could not connect to order-service: {e}, continuing...")

    # 2. Stop running order-service
    print("Step 2: Stopping existing order-service container...")
    run_cmd(["docker", "stop", "order-service"])

    # Clean up any leftover broken container
    run_cmd(["docker", "rm", "-f", BROKEN_CONTAINER])

    # 3. Start order-service with PAYMENT_SERVICE_URL missing
    print("Step 3: Starting container without required PAYMENT_SERVICE_URL...")
    run_cmd([
        "docker", "run", "-d",
        "--name", BROKEN_CONTAINER,
        "--network", "infra_default",
        "-e", "SERVICE_NAME=order-service",
        "-e", "DATABASE_URL=postgresql://chatops:change_me@postgres:5432/chatops",
        "infra-order-service"
    ])

    time.sleep(2.0)

    # 4. Observe symptoms
    print("Step 4: Inspecting container exit state...")
    info = inspect_container(BROKEN_CONTAINER)
    state = info.get("State", {})
    exit_code = state.get("ExitCode", 0)
    status = state.get("Status", "")

    print(f"  Container status: {status}, ExitCode: {exit_code}")

    signals = [
        f"exit_code={exit_code}",
        f"container_status={status}",
        "missing_env_var=PAYMENT_SERVICE_URL",
        "level=CRITICAL"
    ]

    # 5. Extract logs
    print(f"Step 5: Capturing JSON logs to {JSONL_PATH}...")
    json_lines = extract_json_logs(BROKEN_CONTAINER)
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        f.writelines(line + "\n" for line in json_lines)
    print(f"Saved {len(json_lines)} JSON log entries.")

    # 6. Write metadata
    print(f"Step 6: Writing ground truth metadata to {META_PATH}...")
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": SERVICE_NAME,
        "failure_type": "bad_config",
        "root_cause": "PAYMENT_SERVICE_URL environment variable is missing; order-service fails startup check",
        "expected_fix": "Provide PAYMENT_SERVICE_URL in the environment configuration and restart the container",
        "signals": signals,
        "how_to_reproduce": "python infra/failures/bad_env.py"
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/restore.py")


if __name__ == "__main__":
    main()
