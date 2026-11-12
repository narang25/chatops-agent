#!/usr/bin/env python3
"""
Parameterized & Cross-Service Chaos Variant Runner (Task B19 Extension).

Expands the incident dataset across all 3 microservices (`payment-service`,
`order-service`, `inventory-service`) and varied severity parameters
(memory limits 48/64/128MB, error rates 0.20/0.50/0.85, Toxiproxy latencies
1000/2500/5000ms, CPU burn durations 500/1500ms, plus cross-service db_error,
slow_db, and health_fail).

Appends snapshots and manifest records directly to:
  - data/incident_logs/<variant_id>/<run_id>/
  - data/incident_logs/chaos_manifest.jsonl
"""

import argparse
import json
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

FAILURES_DIR = REPO_ROOT / "infra" / "failures"
MANIFEST_PATH = REPO_ROOT / "data" / "incident_logs" / "chaos_manifest.jsonl"
DEPLOY_LOG = REPO_ROOT / "data" / "deploy_events.jsonl"
TOXIPROXY_API = "http://localhost:8474"

SERVICE_URLS = {
    "payment-service": "http://localhost:8001",
    "order-service": "http://localhost:8002",
    "inventory-service": "http://localhost:8003",
}


@dataclass(frozen=True)
class VariantSpec:
    scenario_id: str
    service: str
    failure_type: str
    kind: str
    params: dict[str, Any]


VARIANTS: list[VariantSpec] = [
    # 1. Cross-service health_check_failure (all 3 services)
    VariantSpec("healthfail-payment-v1", "payment-service", "health_check_failure", "health_fail", {}),
    VariantSpec("healthfail-order-v1", "order-service", "health_check_failure", "health_fail", {}),
    VariantSpec("healthfail-inventory-v1", "inventory-service", "health_check_failure", "health_fail", {}),
    # 2. Cross-service db_timeout (all 3 services)
    VariantSpec("dbtimeout-payment-v1", "payment-service", "db_timeout", "slow_db", {}),
    VariantSpec("dbtimeout-order-v1", "order-service", "db_timeout", "slow_db", {}),
    VariantSpec("dbtimeout-inventory-v1", "inventory-service", "db_timeout", "slow_db", {}),
    # 3. Cross-service db_error -> high_error_rate (all 3 services)
    VariantSpec("dberror-payment-v1", "payment-service", "high_error_rate", "db_error", {}),
    VariantSpec("dberror-order-v1", "order-service", "high_error_rate", "db_error", {}),
    VariantSpec("dberror-inventory-v1", "inventory-service", "high_error_rate", "db_error", {}),
    # 4. Parameterized OOM memory limits (48m / 64m / 128m; 32m is below ~39MiB base RSS)
    VariantSpec("oom-payment-48m", "payment-service", "out_of_memory", "oom", {"memory": "48m"}),
    VariantSpec("oom-payment-64m", "payment-service", "out_of_memory", "oom", {"memory": "64m"}),
    VariantSpec("oom-payment-128m", "payment-service", "out_of_memory", "oom", {"memory": "128m"}),
    # 5. Parameterized high_error_rate on order-service (0.20 / 0.50 / 0.85)
    VariantSpec("baddeploy-order-er20", "order-service", "high_error_rate", "error_rate", {"error_rate": 0.20}),
    VariantSpec("baddeploy-order-er50", "order-service", "high_error_rate", "error_rate", {"error_rate": 0.50}),
    VariantSpec("baddeploy-order-er85", "order-service", "high_error_rate", "error_rate", {"error_rate": 0.85}),
    # 6. Parameterized CPU burn durations (500ms / 1500ms)
    VariantSpec("cpusat-payment-500ms", "payment-service", "cpu_saturation", "cpu_burn", {"duration_ms": 500}),
    VariantSpec("cpusat-payment-1500ms", "payment-service", "cpu_saturation", "cpu_burn", {"duration_ms": 1500}),
    # 7. Parameterized Toxiproxy latency tiers (1000ms / 2500ms / 5000ms)
    VariantSpec("nettimeout-order-1000ms", "order-service", "network_timeout", "net_latency", {"latency_ms": 1000}),
    VariantSpec("nettimeout-order-2500ms", "order-service", "network_timeout", "net_latency", {"latency_ms": 2500}),
    VariantSpec("nettimeout-order-5000ms", "order-service", "network_timeout", "net_latency", {"latency_ms": 5000}),
]


def _run_cmd(cmd: list[str]) -> str:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(REPO_ROOT))
    return res.stdout.strip()


def _exercise_service(client: httpx.Client, service: str, count: int = 3) -> None:
    url = SERVICE_URLS[service]
    for i in range(count):
        try:
            if service == "payment-service":
                client.post(f"{url}/pay", json={"order_id": 900 + i, "amount": 19.99}, timeout=8.0)
            elif service == "order-service":
                client.post(f"{url}/orders", json={"item": "widget", "quantity": 1, "amount": 19.99}, timeout=8.0)
            else:
                client.get(f"{url}/stock/widget", timeout=8.0)
        except Exception:
            pass


def _inspect_restarts(container: str) -> tuple[int, bool, int]:
    raw = _run_cmd(["docker", "inspect", container])
    try:
        info = json.loads(raw)[0]
        state = info.get("State", {})
        return int(info.get("RestartCount", 0)), bool(state.get("OOMKilled", False)), int(state.get("ExitCode", 0))
    except Exception:
        return 0, False, 0


def inject_variant(spec: VariantSpec) -> dict[str, Any]:
    """Execute one parameterized variant and return its ground_truth dict."""
    svc = spec.service
    url = SERVICE_URLS[svc]
    signals: list[str] = []
    client = httpx.Client(timeout=10.0)

    if spec.kind == "health_fail":
        client.post(f"{url}/admin/fault", json={"health_fail": True})
        for _ in range(3):
            resp = client.get(f"{url}/health")
            signals.append(f"health_http_{resp.status_code}")
        root_cause = f"Health check toggle health_fail set to true on {svc}; GET /health returns 500"
        expected_fix = f"Reset health_fail=false via POST /admin/fault or restart {svc}"

    elif spec.kind == "slow_db":
        client.post(f"{url}/admin/fault", json={"slow_db": True})
        _exercise_service(client, svc, count=3)
        signals.extend(["fault_slow_db=true", f"service={svc}"])
        root_cause = f"Slow DB fault active on {svc} adding 3s delay per database connection"
        expected_fix = f"Disable slow_db fault via POST /admin/fault on {svc}"

    elif spec.kind == "db_error":
        client.post(f"{url}/admin/fault", json={"db_error": True})
        _exercise_service(client, svc, count=5)
        signals.extend(["fault_db_error=true", f"service={svc}", "http_status_500"])
        root_cause = f"Database error fault enabled on {svc}; DB operations fail with simulated exception"
        expected_fix = f"Disable db_error fault via POST /admin/fault on {svc}"

    elif spec.kind == "oom":
        mem = spec.params["memory"]
        base_restarts, _, _ = _inspect_restarts(svc)
        _run_cmd(["docker", "update", "--memory", mem, "--memory-swap", mem, svc])
        for _ in range(18):
            try:
                client.get(f"{url}/leak", timeout=3.0)
            except Exception:
                pass
            time.sleep(0.6)
            restarts, oom_killed, exit_code = _inspect_restarts(svc)
            if oom_killed or exit_code == 137 or restarts > base_restarts:
                signals.extend([f"oom_killed={str(oom_killed).lower()}", f"exit_code={exit_code}", f"memory_limit={mem}"])
                break
        else:
            signals.append(f"memory_limit={mem}")
        root_cause = f"Container memory limit ({mem}) on {svc} exhausted by /leak allocations"
        expected_fix = f"Raise memory limit above {mem} (e.g. 256MB) and fix leak in {svc}"

    elif spec.kind == "error_rate":
        rate = float(spec.params["error_rate"])
        DEPLOY_LOG.parent.mkdir(parents=True, exist_ok=True)
        deploy_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": svc,
            "action": "deploy",
            "image": f"infra-{svc}:bad-er{int(rate * 100)}",
            "trigger": "chaos_variants injection",
            "scenario_id": spec.scenario_id,
            "description": f"Simulated bad deploy on {svc} with {int(rate * 100)}% error rate",
        }
        with open(DEPLOY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(deploy_event) + "\n")
        client.post(f"{url}/admin/fault", json={"error_rate": rate})
        _exercise_service(client, svc, count=10)
        signals.extend([f"error_rate={rate}", "deploy_event_recorded"])
        root_cause = f"Recent deployment on {svc} introduced error_rate={rate} fault returning HTTP 500"
        expected_fix = f"Rollback deploy or reset error_rate=0.0 on {svc}"

    elif spec.kind == "cpu_burn":
        dur = int(spec.params["duration_ms"])
        for _ in range(4):
            try:
                client.get(f"{url}/burn?duration_ms={dur}", timeout=15.0)
            except Exception:
                pass
        signals.extend([f"cpu_burn_duration_ms={dur}", "cpu_limit=0.5_cpus"])
        root_cause = f"CPU saturation on {svc} from /burn cycles (duration_ms={dur}) hitting 0.5 CPU quota"
        expected_fix = f"Throttle compute workload or increase CPU limit on {svc}"

    elif spec.kind == "net_latency":
        lat_ms = int(spec.params["latency_ms"])
        jitter_ms = max(100, lat_ms // 5)
        try:
            client.delete(f"{TOXIPROXY_API}/proxies/payment-proxy")
            client.post(
                f"{TOXIPROXY_API}/proxies",
                json={"name": "payment-proxy", "listen": "0.0.0.0:8101", "upstream": "payment-service:8000", "enabled": True},
            )
            client.post(
                f"{TOXIPROXY_API}/proxies/payment-proxy/toxics",
                json={"name": "payment-latency", "type": "latency", "stream": "downstream", "attributes": {"latency": lat_ms, "jitter": jitter_ms}},
            )
            for _ in range(3):
                try:
                    client.get("http://localhost:8101/health", timeout=min(4.0, lat_ms / 1000.0))
                except Exception:
                    signals.append("request_timeout")
        except Exception:
            client.post(f"{url}/admin/fault", json={"slow_db": True})
            signals.append("fallback_slow_db_fault=true")
        _exercise_service(client, svc, count=3)
        signals.extend([f"toxiproxy_latency={lat_ms}ms", f"toxiproxy_jitter={jitter_ms}ms"])
        root_cause = f"Toxiproxy injects {lat_ms}ms (+{jitter_ms}ms jitter) network latency upstream of {svc}"
        expected_fix = "Remove Toxiproxy payment-latency toxic and check downstream network latency"

    else:
        raise ValueError(f"Unsupported variant kind: {spec.kind}")

    return {
        "scenario_id": spec.scenario_id,
        "service": svc,
        "failure_type": spec.failure_type,
        "root_cause": root_cause,
        "expected_fix": expected_fix,
        "signals": list(dict.fromkeys(signals)),
        "parameters": spec.params,
    }


def restore_system(dry_run: bool = False) -> None:
    if dry_run:
        return
    subprocess.run(
        [sys.executable, str(FAILURES_DIR / "run_scenario.py"), "restore"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(REPO_ROOT),
    )
    time.sleep(2.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parameterized & Cross-Service Chaos Variant Runner")
    parser.add_argument("--repeat", type=int, default=3, help="Repetitions per variant")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for shuffling")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without mutating containers")
    args = parser.parse_args()

    random.seed(args.seed)
    run_plan: list[tuple[int, VariantSpec]] = []
    for rep in range(1, args.repeat + 1):
        shuffled = list(VARIANTS)
        random.shuffle(shuffled)
        for spec in shuffled:
            run_plan.append((rep, spec))

    from infra.failures.recorder import record_incident_snapshot

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    total_runs = len(run_plan)

    for idx, (rep, spec) in enumerate(run_plan, start=1):
        started_at = datetime.now(timezone.utc).isoformat()
        run_id = f"{spec.scenario_id}_r{rep}_{int(time.time())}"

        snapshot_dir: str | None = None
        if not args.dry_run:
            try:
                gt = inject_variant(spec)
                time.sleep(2.0)
                snapshot_dir = str(
                    record_incident_snapshot(
                        spec.scenario_id,
                        spec.service,
                        run_id=run_id,
                        minutes=3,
                        ground_truth=gt,
                    )
                )
            except Exception as exc:
                snapshot_dir = f"recording_error: {exc}"
            finally:
                restore_system(dry_run=False)

        record = {
            "run_id": run_id,
            "scenario_id": spec.scenario_id,
            "service": spec.service,
            "failure_type": spec.failure_type,
            "started_at": started_at,
            "snapshot_dir": snapshot_dir,
            "repetition": rep,
            "run_index": idx,
            "total_runs": total_runs,
            "parameters": spec.params,
        }
        print(json.dumps(record), flush=True)
        if not args.dry_run:
            with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    main()
