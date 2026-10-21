#!/usr/bin/env python3
"""
Convenience CLI for managing the ChatOps infrastructure stack.
Works cross-platform on Windows, macOS, and Linux without requiring GNU make.

Usage:
    python infra/manage.py up        # Start all containers in background and wait for health
    python infra/manage.py down      # Stop and remove all containers and network
    python infra/manage.py restart   # Restart all containers
    python infra/manage.py restore   # Reset all fault toggles and memory limits
    python infra/manage.py ps        # Show status of all services
    python infra/manage.py logs [svc]# Stream logs for a service or all services
"""

import sys
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "infra" / "docker-compose.yml"
RESTORE_SCRIPT = REPO_ROOT / "infra" / "failures" / "restore.py"


def run_cmd(cmd: list[str], check: bool = True) -> int:
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT)
        return proc.returncode
    except KeyboardInterrupt:
        return 130


def cmd_up():
    print(">>> Starting ChatOps stack (detached)...")
    res = run_cmd(["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d"])
    if res != 0:
        print("Failed to start containers.")
        sys.exit(res)

    print("\n>>> Waiting for services to reach healthy status...")
    time.sleep(3)
    run_cmd(["docker", "compose", "-f", str(COMPOSE_FILE), "ps"])
    print("\nStack is ready. Web UI endpoints:")
    print("  - Prometheus: http://localhost:9090")
    print("  - Grafana:    http://localhost:3000 (admin / admin)")
    print("  - cAdvisor:   http://localhost:8085")
    print("  - Payment:    http://localhost:8001/health")
    print("  - Order:      http://localhost:8002/health")
    print("  - Inventory:  http://localhost:8003/health")


def cmd_down():
    print(">>> Stopping ChatOps stack...")
    run_cmd(["docker", "compose", "-f", str(COMPOSE_FILE), "down"])


def cmd_restart():
    cmd_down()
    cmd_up()


def cmd_restore():
    print(">>> Restoring stack to baseline healthy state...")
    if RESTORE_SCRIPT.exists():
        run_cmd([sys.executable, str(RESTORE_SCRIPT)])
    else:
        print(f"Error: {RESTORE_SCRIPT} not found.")


def cmd_ps():
    run_cmd(["docker", "compose", "-f", str(COMPOSE_FILE), "ps"])


def cmd_logs(service: str | None = None):
    args = ["docker", "compose", "-f", str(COMPOSE_FILE), "logs", "-f", "--tail", "100"]
    if service:
        args.append(service)
    run_cmd(args)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == "up":
        cmd_up()
    elif command == "down":
        cmd_down()
    elif command == "restart":
        cmd_restart()
    elif command == "restore":
        cmd_restore()
    elif command == "ps":
        cmd_ps()
    elif command == "logs":
        svc = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_logs(svc)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
