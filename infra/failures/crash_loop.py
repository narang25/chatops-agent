#!/usr/bin/env python3
"""
Failure Scenario: crash_loop on payment-service.

Injects a crash loop by starting a separate payment-service container
that immediately exits (exit code 1) with --restart=always so Docker
keeps restarting it. The main compose payment-service is stopped first
to free the port, then the crash-looping container takes its place.

Workflow:
1. Verify payment-service is healthy.
2. Stop the running payment-service container.
3. Start a crash-looping container (overrides CMD to: python -c "sys.exit(1)").
4. Observe: RestartCount rising, exit code 1, back-off in Docker events.
5. Extract logs and write ground truth metadata.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import httpx

SCENARIO_ID = "crashloop-payment-001"
SERVICE_NAME = "payment-service"
CRASH_CONTAINER = "payment-service-crashloop"
SERVICE_URL = "http://localhost:8001"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.path.join(REPO_ROOT, "data", "incident_logs")
JSONL_PATH = os.path.join(LOG_DIR, f"{SCENARIO_ID}.jsonl")
META_PATH = os.path.join(LOG_DIR, f"{SCENARIO_ID}.meta.json")


def run_cmd(cmd: list[str]) -> tuple[str, str]:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout.strip(), res.stderr.strip()


def inspect_container(container: str) -> dict:
    stdout, _ = run_cmd(["docker", "inspect", container])
    try:
        data = json.loads(stdout)
        return data[0] if data else {}
    except Exception:
        return {}


def extract_json_logs(container: str) -> list[str]:
    stdout, _ = run_cmd(["docker", "logs", container])
    valid_lines = []
    for line in stdout.splitlines():
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

    # 1. Verify initial health
    print("Step 1: Checking initial health of payment-service...")
    try:
        resp = client.get(f"{SERVICE_URL}/health", timeout=3.0)
        print(f"  payment-service: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Warning: could not connect ({e}), continuing...")

    # 2. Stop running payment-service
    print("Step 2: Stopping existing payment-service container...")
    run_cmd(["docker", "stop", "payment-service"])
    run_cmd(["docker", "rm", "-f", CRASH_CONTAINER])
    time.sleep(1.0)

    # 3. Detect the docker network and image used by the stack
    stdout, _ = run_cmd(["docker", "network", "ls", "--filter", "name=infra", "--format", "{{.Name}}"])
    network = stdout.strip().split("\n")[0] if stdout.strip() else "infra_default"
    print(f"  Using Docker network: {network}")

    # Find the image used by payment-service
    stdout, _ = run_cmd([
        "docker", "inspect", "payment-service",
        "--format", "{{.Config.Image}}",
    ])
    image = stdout.strip() or "infra-payment-service"
    print(f"  Using image: {image}")

    # 4. Start crash-looping container
    print(f"Step 3: Starting crash-loop container ({CRASH_CONTAINER})...")
    _, err = run_cmd([
        "docker", "run", "-d",
        "--name", CRASH_CONTAINER,
        "--network", network,
        "--restart", "always",
        "-e", "SERVICE_NAME=payment-service",
        "-e", "DATABASE_URL=postgresql://chatops:change_me@postgres:5432/chatops",
        image,
        "python", "-c",
        "import sys, json, datetime; "
        "now = datetime.datetime.now(datetime.timezone.utc); "
        "ts = now.strftime('%Y-%m-%dT%H:%M:%S.') + f'{now.microsecond // 1000:03d}Z'; "
        "print(json.dumps({'timestamp': ts, 'service': 'payment-service', 'level': 'CRITICAL', "
        "'message': 'Startup failed: crash_loop fault injected — exiting with code 1'}), flush=True); "
        "sys.exit(1)",
    ])
    if err:
        print(f"  docker run stderr: {err[:200]}")

    time.sleep(1.0)

    # 5. Wait for restart count to grow (up to 30s)
    print("Step 4: Waiting for restart loop to establish...")
    initial_info = inspect_container(CRASH_CONTAINER)
    initial_restarts = initial_info.get("RestartCount", 0)
    signals: list[str] = ["crash_loop_container_started", "exit_code=1"]

    for attempt in range(15):
        time.sleep(2.0)
        info = inspect_container(CRASH_CONTAINER)
        restarts = info.get("RestartCount", 0)
        state = info.get("State", {})
        exit_code = state.get("ExitCode", 0)
        status = state.get("Status", "")
        print(f"  Attempt {attempt + 1}: status={status}, exit_code={exit_code}, restart_count={restarts}")
        if restarts > initial_restarts or status in ("restarting", "exited"):
            signals.append(f"restart_count_increased_to_{restarts}")
            signals.append("container_state=restarting_or_exited")
            print(f"  => Crash loop confirmed! RestartCount={restarts}")
            break
    else:
        signals.append("crash_loop_detection_timeout")

    signals.extend([
        "exit_code=1",
        "restart_count_increasing",
        "docker_restart_policy=always",
    ])

    # 6. Extract logs
    print(f"Step 5: Capturing JSON logs to {JSONL_PATH}...")
    json_lines = extract_json_logs(CRASH_CONTAINER)
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for line in json_lines:
            f.write(line + "\n")
    print(f"Saved {len(json_lines)} JSON log entries.")

    # 7. Write metadata
    print(f"Step 6: Writing ground truth metadata to {META_PATH}...")
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": SERVICE_NAME,
        "failure_type": "crash_loop",
        "root_cause": (
            "payment-service container overridden with a CMD that always exits 1 "
            "and Docker restart=always keeps restarting it. "
            "Each restart attempt fails immediately, incrementing RestartCount "
            "and triggering Docker's exponential back-off."
        ),
        "expected_fix": (
            "Stop the crash-looping container and restart the original: "
            "docker stop payment-service-crashloop && docker rm payment-service-crashloop, "
            "then docker compose -f infra/docker-compose.yml up -d payment-service. "
            "In production: fix the startup code/configuration causing exit 1."
        ),
        "signals": list(dict.fromkeys(signals)),
        "how_to_reproduce": "python infra/failures/run_scenario.py run crashloop-payment-001",
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/run_scenario.py restore")


if __name__ == "__main__":
    main()
