#!/usr/bin/env python3
"""
Failure Scenario: disk_full on inventory-service.

Workflow:
1. Verify inventory-service is healthy.
2. Call GET /fill repeatedly until [Errno 28] No space left on device is returned.
3. Confirm the disk-full error appears in container logs.
4. Leave fill file in place (caller must run restore to clean up).
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import httpx

SCENARIO_ID = "diskfull-inventory-001"
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
    print("Step 1: Checking initial health of inventory-service...")
    try:
        resp = client.get(f"{SERVICE_URL}/health", timeout=3.0)
        if resp.status_code != 200:
            print(f"Warning: inventory-service returned {resp.status_code}, continuing...")
        else:
            print("Inventory service is healthy.")
    except Exception as e:
        print(f"Warning: could not connect: {e}, continuing...")

    since_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Fill disk by calling /fill repeatedly
    print("Step 2: Filling disk via GET /fill (chunk=10240KB each call)...")
    signals = []
    disk_full_detected = False

    for i in range(1, 200):  # up to ~2GB of writes; stops at ENOSPC
        try:
            resp = client.get(f"{SERVICE_URL}/fill?chunk_kb=10240", timeout=15.0)
            data = resp.json()
            if resp.status_code == 507 or data.get("disk_full"):
                print(f"  => Disk full detected on call {i}: {data.get('error')}")
                signals.append("errno_28_no_space_left_on_device")
                signals.append(f"disk_full=true")
                signals.append(f"http_status_507")
                disk_full_detected = True
                break
            total_mb = data.get("total_fill_mb", 0)
            print(f"  Fill call {i}: total={total_mb:.1f}MB written")
            if i % 5 == 0:
                time.sleep(0.2)
        except Exception as e:
            print(f"  Fill call {i} error: {e}")
            signals.append("connection_error_during_fill")
            break

    if not disk_full_detected:
        print("Warning: disk full not detected — container may have large writable layer.")
        print("  This scenario works best with --storage-opt size=100m on the container.")
        signals.append("fill_attempted_no_enospc_detected")
        signals.append("disk_usage_increasing")

    # 3. Extract logs
    print(f"Step 3: Capturing JSON logs to {JSONL_PATH}...")
    json_lines = extract_json_logs(CONTAINER_NAME, since_ts)
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for line in json_lines:
            f.write(line + "\n")
    print(f"Saved {len(json_lines)} JSON log entries.")

    # 4. Write metadata
    print(f"Step 4: Writing ground truth metadata to {META_PATH}...")
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": SERVICE_NAME,
        "failure_type": "disk_full",
        "root_cause": (
            "The /fill endpoint writes 10MB chunks to /tmp/disk_fill_payload "
            "until [Errno 28] No space left on device is raised, exhausting "
            "the container's writable layer disk allocation"
        ),
        "expected_fix": (
            "Call DELETE /fill/reset to remove the fill payload file and reclaim space. "
            "In production: add disk usage alerting and implement log rotation / data purging"
        ),
        "signals": list(dict.fromkeys(signals)) if signals else [
            "errno_28_no_space_left_on_device",
            "http_status_507",
            "disk_full=true",
            "app_errors_total_increasing",
        ],
        "how_to_reproduce": "python infra/failures/run_scenario.py run diskfull-inventory-001",
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/run_scenario.py restore")


if __name__ == "__main__":
    main()
