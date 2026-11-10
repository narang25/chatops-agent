#!/usr/bin/env python3
"""
Unified Failure Scenario Runner for ChatOps Benchmark & Local Testing.

Interface:
    python infra/failures/run_scenario.py list
        Outputs a JSON array of all registered scenario IDs with metadata.

    python infra/failures/run_scenario.py run <scenario_id>
        Executes failure injection without restoring, waits for symptoms,
        and outputs a single JSON line:
        {"status": "injected", "scenario_id": "...", "service": "...",
         "failure_type": "...", "ground_truth": {...}}

    python infra/failures/run_scenario.py restore
        Restores all containers, memory limits, and fault toggles to healthy.

    python infra/failures/run_scenario.py validate
        Validates that all ground truth files match contracts/failure_types.md.
"""

import json
import sys
from pathlib import Path

FAILURES_DIR = Path(__file__).resolve().parent
REPO_ROOT = FAILURES_DIR.parent.parent
GROUND_TRUTH_DIR = FAILURES_DIR / "ground_truth"

# ── Canonical failure types (from contracts/failure_types.md) ────────────────
VALID_FAILURE_TYPES = {
    "out_of_memory",
    "bad_config",
    "health_check_failure",
    "db_timeout",
    "dependency_failure",
    "disk_full",
    "cpu_saturation",
    "crash_loop",
    "network_timeout",
    "high_error_rate",
}

# ── Scenario registry ─────────────────────────────────────────────────────────
# Each entry maps scenario_id → injection script + expected metadata.
# failure_type MUST be a value in VALID_FAILURE_TYPES.
SCENARIOS = {
    # ── Week 1-2 scenarios ────────────────────────────────────────────────
    "oom-payment-001": {
        "script": "oom.py",
        "service": "payment-service",
        "failure_type": "out_of_memory",
        "description": "Payment service memory leak leading to OOM crash (exit 137)",
    },
    "badenv-order-001": {
        "script": "bad_env.py",
        "service": "order-service",
        "failure_type": "bad_config",
        "description": "Order service missing PAYMENT_SERVICE_URL causing startup crash (exit 1)",
    },
    "healthfail-inventory-001": {
        "script": "health_fail.py",
        "service": "inventory-service",
        "failure_type": "health_check_failure",
        "description": "Inventory service /health returns 500 via fault toggle",
    },
    "dbtimeout-payment-001": {
        "script": "db_timeout.py",
        "service": "payment-service",
        "failure_type": "db_timeout",
        "description": "Payment service slow DB fault (3s delay per query) causing timeouts",
    },
    "depfail-order-001": {
        "script": "dependency_failure.py",
        "service": "order-service",
        "failure_type": "dependency_failure",
        "description": "Downstream payment-service stopped causing 502 errors in order-service",
    },
    "cpusat-payment-001": {
        "script": "cpu_saturation.py",
        "service": "payment-service",
        "failure_type": "cpu_saturation",
        "description": "Payment service /burn endpoint saturating 0.5 CPU quota",
    },
    # ── Week 4 scenarios (B16) ────────────────────────────────────────────
    "diskfull-inventory-001": {
        "script": "disk_full.py",
        "service": "inventory-service",
        "failure_type": "disk_full",
        "description": "Inventory service /fill endpoint exhausts container writable layer disk space",
    },
    "nettimeout-order-001": {
        "script": "network_timeout.py",
        "service": "order-service",
        "failure_type": "network_timeout",
        "description": "Toxiproxy injects 3s latency between order-service and payment-service",
    },
    "baddeploy-order-001": {
        "script": "bad_deploy.py",
        "service": "order-service",
        "failure_type": "high_error_rate",
        "description": "Simulated bad deploy: order-service returns 500 on 50% of requests",
    },
    "crashloop-payment-001": {
        "script": "crash_loop.py",
        "service": "payment-service",
        "failure_type": "crash_loop",
        "description": "Payment service crashes repeatedly with exit code 1, entering restart backoff",
    },
}


# ── Ground truth loader ───────────────────────────────────────────────────────

def _load_ground_truth(scenario_id: str) -> dict | None:
    """Load ground truth JSON for a scenario, or return None if not found."""
    path = GROUND_TRUTH_DIR / f"{scenario_id}.meta.json"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            print(
                json.dumps({"warning": f"Could not load ground truth for {scenario_id}: {exc}"}),
                file=sys.stderr,
            )
    return None


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_all() -> list[str]:
    """Return a list of validation errors across all registered scenarios."""
    errors: list[str] = []

    for scenario_id, info in SCENARIOS.items():
        ft = info["failure_type"]
        if ft not in VALID_FAILURE_TYPES:
            errors.append(
                f"{scenario_id}: failure_type '{ft}' not in contracts/failure_types.md"
            )

        gt = _load_ground_truth(scenario_id)
        if gt is None:
            errors.append(f"{scenario_id}: missing ground_truth/{scenario_id}.meta.json")
            continue

        gt_ft = gt.get("failure_type", "")
        if gt_ft != ft:
            errors.append(
                f"{scenario_id}: ground truth failure_type '{gt_ft}' "
                f"!= registry failure_type '{ft}'"
            )

        if gt_ft not in VALID_FAILURE_TYPES:
            errors.append(
                f"{scenario_id}: ground truth failure_type '{gt_ft}' "
                f"not in contracts/failure_types.md"
            )

        for required in ("root_cause", "expected_fix", "signals"):
            if not gt.get(required):
                errors.append(f"{scenario_id}: ground truth missing field '{required}'")

    return errors


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list() -> None:
    scenario_list = [
        {
            "scenario_id": sid,
            "service": info["service"],
            "failure_type": info["failure_type"],
            "description": info["description"],
            "has_ground_truth": (GROUND_TRUTH_DIR / f"{sid}.meta.json").exists(),
        }
        for sid, info in SCENARIOS.items()
    ]
    print(json.dumps(scenario_list, indent=2))


def cmd_run(scenario_id: str) -> None:
    import subprocess

    if scenario_id not in SCENARIOS:
        print(
            json.dumps(
                {
                    "error": f"Unknown scenario_id: '{scenario_id}'",
                    "available": list(SCENARIOS.keys()),
                }
            )
        )
        sys.exit(1)

    info = SCENARIOS[scenario_id]
    script_path = FAILURES_DIR / info["script"]

    if not script_path.exists():
        print(json.dumps({"error": f"Injection script not found: {script_path}"}))
        sys.exit(1)

    # Run injection script
    proc = subprocess.run([sys.executable, str(script_path)], cwd=REPO_ROOT)
    if proc.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "scenario_id": scenario_id,
                    "returncode": proc.returncode,
                }
            )
        )
        sys.exit(proc.returncode)

    # Load ground truth
    ground_truth = _load_ground_truth(scenario_id)

    # Stable JSON summary line (format Person A's benchmark depends on)
    result = {
        "status": "injected",
        "scenario_id": scenario_id,
        "service": info["service"],
        "failure_type": info["failure_type"],
    }
    if ground_truth:
        result["ground_truth"] = ground_truth

    print(json.dumps(result))


def cmd_restore() -> None:
    import subprocess

    restore_script = FAILURES_DIR / "restore.py"
    if not restore_script.exists():
        print(json.dumps({"error": f"Restore script not found: {restore_script}"}))
        sys.exit(1)

    proc = subprocess.run([sys.executable, str(restore_script)], cwd=REPO_ROOT)
    sys.exit(proc.returncode)


def cmd_validate() -> None:
    errors = _validate_all()
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        sys.exit(1)
    else:
        print(
            json.dumps(
                {
                    "valid": True,
                    "scenarios_checked": len(SCENARIOS),
                    "message": "All scenarios have valid ground truth matching contracts/failure_types.md",
                }
            )
        )


# ── Startup validation (warn, don't block) ────────────────────────────────────

def _startup_check() -> None:
    """Print warnings for any validation issues, but don't exit."""
    # Only warn about missing ground truth for existing scripts (B16 scripts
    # may not exist yet). Skip gracefully for unbuilt scenarios.
    for scenario_id, info in SCENARIOS.items():
        script_path = FAILURES_DIR / info["script"]
        if not script_path.exists():
            continue  # Script not built yet — skip silently
        ft = info["failure_type"]
        if ft not in VALID_FAILURE_TYPES:
            print(
                f"[WARNING] run_scenario: {scenario_id} has invalid failure_type '{ft}'",
                file=sys.stderr,
            )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    _startup_check()

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "list":
        cmd_list()
    elif action == "run":
        if len(sys.argv) < 3:
            print("Error: scenario_id is required for 'run'.")
            print("Usage: python infra/failures/run_scenario.py run <scenario_id>")
            sys.exit(1)
        cmd_run(sys.argv[2])
    elif action == "restore":
        cmd_restore()
    elif action == "validate":
        cmd_validate()
    else:
        print(f"Unknown action: '{action}'")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
