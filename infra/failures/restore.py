#!/usr/bin/env python3
"""
Restore script: Returns all ChatOps services to a completely healthy state.

1. Restores memory limit on payment-service to 128MB.
2. Removes any temporary badenv container and ensures order-service is running from docker-compose.
3. Resets all fault injection toggles across all services.
4. Verifies all services respond with 200 OK on /health.
"""

import subprocess
import time

import httpx

SERVICES = [
    ("payment-service", "http://localhost:8001"),
    ("order-service", "http://localhost:8002"),
    ("inventory-service", "http://localhost:8003"),
]


def run_cmd(cmd: list[str]) -> str:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout.strip()


def main():
    print("=== Restoring ChatOps Stack to Healthy State ===")

    # 1. Reset memory limits
    print("1. Restoring memory limit on payment-service (128MB)...")
    run_cmd(["docker", "update", "--memory", "128m", "--memory-swap", "128m", "payment-service"])

    # 2. Clean up temporary broken containers and ensure compose stack is up
    print("2. Ensuring clean compose container state...")
    run_cmd(["docker", "rm", "-f", "order-service-badenv"])
    run_cmd(["docker", "compose", "-f", "infra/docker-compose.yml", "up", "-d"])

    time.sleep(3.0)

    # 3. Reset fault toggles via /admin/fault
    print("3. Resetting fault toggles on all services...")
    client = httpx.Client(timeout=3.0)
    for name, url in SERVICES:
        try:
            resp = client.post(
                f"{url}/admin/fault",
                json={"health_fail": False, "slow_db": False, "db_error": False},
            )
            print(f"  {name}: faults reset -> {resp.text}")
        except Exception as e:
            print(f"  {name}: could not reach /admin/fault ({e})")

    # 4. Verify health checks
    print("\n4. Verifying health checks:")
    all_healthy = True
    for name, url in SERVICES:
        try:
            resp = client.get(f"{url}/health")
            if resp.status_code == 200:
                print(f"  [OK] {name} is healthy: {resp.text}")
            else:
                print(f"  [FAIL] {name} returned status {resp.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"  [FAIL] {name} connection error: {e}")
            all_healthy = False

    if all_healthy:
        print("\n=== All Services Successfully Restored to Healthy State ===")
    else:
        print("\n=== Some services still reporting issues, check docker compose ps ===")


if __name__ == "__main__":
    main()
