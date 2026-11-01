"""
Incident Recorder for ChatOps Benchmark & Chaos Suite (Task B19).

Captures a complete snapshot of system state after a scenario injection:
    - logs.jsonl        (container logs in JSON format)
    - metrics.json      (key Prometheus metrics snapshot)
    - events.json       (Docker lifecycle events)
    - pod_status.json   (get_pod_status contract shape)
    - ground_truth.json (ground truth .meta.json for scoring)
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INCIDENT_LOGS_DIR = REPO_ROOT / "data" / "incident_logs"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")


def record_incident_snapshot(
    scenario_id: str,
    service: str,
    run_id: str | None = None,
    minutes: int = 5,
) -> Path:
    """
    Take an incident snapshot and write files to data/incident_logs/<scenario_id>/<run_id>/.
    Returns the snapshot directory Path.
    """
    if not run_id:
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_id = f"{scenario_id}_{now_str}"

    snapshot_dir = INCIDENT_LOGS_DIR / scenario_id / run_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    now_ts = time.time()
    since_ts = now_ts - (minutes * 60)
    since_iso = datetime.fromtimestamp(since_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Capture logs.jsonl
    logs_file = snapshot_dir / "logs.jsonl"
    log_lines = []
    try:
        cmd = ["docker", "logs", "--since", since_iso, service]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0)
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                log_lines.append(json.dumps(parsed))
            except Exception:
                log_lines.append(json.dumps({
                    "timestamp": since_iso,
                    "level": "INFO",
                    "service": service,
                    "message": line,
                }))
    except Exception as exc:
        log_lines.append(json.dumps({"error": f"Failed extracting logs: {exc}"}))

    with open(logs_file, "w", encoding="utf-8") as f:
        for line in log_lines:
            f.write(line + "\n")

    # 2. Capture metrics.json
    metrics_file = snapshot_dir / "metrics.json"
    metrics_snapshot: dict[str, Any] = {"service": service, "timestamp": since_iso, "metrics": {}}
    try:
        from mcp_servers.prometheus.server import get_metrics
        for m_name in ["http_requests_total", "app_errors_total", "app_memory_bytes", "app_up"]:
            res = get_metrics(service, m_name, minutes=minutes)
            metrics_snapshot["metrics"][m_name] = res.get("latest")
    except Exception as exc:
        metrics_snapshot["error"] = str(exc)

    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics_snapshot, f, indent=2)

    # 3. Capture pod_status.json
    status_file = snapshot_dir / "pod_status.json"
    status_data = {}
    try:
        from mcp_servers.kubernetes.server import get_pod_status
        status_data = get_pod_status(service)
    except Exception as exc:
        status_data = {"error": str(exc)}

    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2)

    # 4. Capture events.json
    events_file = snapshot_dir / "events.json"
    events_data = {}
    try:
        from mcp_servers.kubernetes.server import get_events
        events_data = get_events(service, minutes=minutes)
    except Exception as exc:
        events_data = {"error": str(exc)}

    with open(events_file, "w", encoding="utf-8") as f:
        json.dump(events_data, f, indent=2)

    # 5. Capture ground_truth.json
    gt_file = snapshot_dir / "ground_truth.json"
    canonical_gt = REPO_ROOT / "infra" / "failures" / "ground_truth" / f"{scenario_id}.meta.json"
    secret_gt = REPO_ROOT / "infra" / "failures" / "ground_truth_secret" / f"{scenario_id}.meta.json"
    src_gt = canonical_gt if canonical_gt.exists() else secret_gt

    if src_gt.exists():
        try:
            with open(src_gt, "r", encoding="utf-8") as f_in, open(gt_file, "w", encoding="utf-8") as f_out:
                f_out.write(f_in.read())
        except Exception:
            pass

    return snapshot_dir
