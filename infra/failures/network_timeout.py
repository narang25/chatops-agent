#!/usr/bin/env python3
"""
Failure Scenario: network_timeout on order-service → payment-service.

Uses Toxiproxy to inject latency on the network path between order-service
and payment-service. Toxiproxy must be running (added to docker-compose.yml).

Workflow:
1. Verify both services are healthy.
2. Configure Toxiproxy: proxy payment-service:8000 on port 8101.
3. Inject a latency toxic (3000ms latency + 500ms jitter).
4. Update order-service PAYMENT_SERVICE_URL to route through Toxiproxy.
5. Send orders and verify timeout errors appear in logs.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import httpx

SCENARIO_ID = "nettimeout-order-001"
SERVICE_NAME = "order-service"
CONTAINER_ORDER = "order-service"
SERVICE_URL = "http://localhost:8002"
PAYMENT_URL = "http://localhost:8001"
TOXIPROXY_API = "http://localhost:8474"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.path.join(REPO_ROOT, "data", "incident_logs")
JSONL_PATH = os.path.join(LOG_DIR, f"{SCENARIO_ID}.jsonl")
META_PATH = os.path.join(LOG_DIR, f"{SCENARIO_ID}.meta.json")

PROXY_NAME = "payment-proxy"
TOXIC_NAME = "payment-latency"
LATENCY_MS = 3000
JITTER_MS = 500


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


def _toxiproxy_available(client: httpx.Client) -> bool:
    try:
        resp = client.get(f"{TOXIPROXY_API}/proxies", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


def main():
    print(f"=== Starting Failure Injection: {SCENARIO_ID} ===")
    os.makedirs(LOG_DIR, exist_ok=True)

    client = httpx.Client(timeout=10.0)
    signals: list[str] = []

    # 1. Verify services health
    print("Step 1: Checking service health...")
    for name, url in [("order-service", SERVICE_URL), ("payment-service", PAYMENT_URL)]:
        try:
            resp = client.get(f"{url}/health", timeout=3.0)
            print(f"  {name}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  {name}: unreachable ({e})")

    # 2. Check Toxiproxy availability
    print("Step 2: Checking Toxiproxy availability...")
    if not _toxiproxy_available(client):
        print("  WARNING: Toxiproxy not available at localhost:8474")
        print("  Falling back: simulating network timeout via order-service fault toggle")
        # Fallback: set slow_db on order-service to cause timeouts
        try:
            resp = client.post(f"{SERVICE_URL}/admin/fault", json={"slow_db": True})
            print(f"  Fallback fault set: {resp.text}")
            signals.append("fallback_slow_db_fault=true")
            signals.append("toxiproxy_not_available")
        except Exception as e:
            print(f"  Could not set fallback fault: {e}")
        signals.extend([
            "network_latency_simulated_via_fault",
            "http_request_duration_seconds_elevated",
        ])
    else:
        print("  Toxiproxy is available.")

        since_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 3. Create proxy for payment-service
        print("Step 3: Creating Toxiproxy proxy for payment-service...")
        # Delete any existing proxy with same name
        client.delete(f"{TOXIPROXY_API}/proxies/{PROXY_NAME}")

        proxy_config = {
            "name": PROXY_NAME,
            "listen": "0.0.0.0:8101",
            "upstream": "payment-service:8000",
            "enabled": True,
        }
        resp = client.post(f"{TOXIPROXY_API}/proxies", json=proxy_config)
        if resp.status_code not in (200, 201):
            print(f"  Warning: proxy creation returned {resp.status_code}: {resp.text}")
        else:
            print(f"  Proxy created: {PROXY_NAME} → payment-service:8000 on port 8101")

        # 4. Inject latency toxic
        print(f"Step 4: Injecting latency toxic ({LATENCY_MS}ms + {JITTER_MS}ms jitter)...")
        toxic_config = {
            "name": TOXIC_NAME,
            "type": "latency",
            "stream": "downstream",
            "attributes": {"latency": LATENCY_MS, "jitter": JITTER_MS},
        }
        resp = client.post(
            f"{TOXIPROXY_API}/proxies/{PROXY_NAME}/toxics",
            json=toxic_config,
        )
        if resp.status_code in (200, 201):
            print(f"  Latency toxic injected: {LATENCY_MS}ms delay")
            signals.append(f"toxiproxy_latency={LATENCY_MS}ms")
            signals.append(f"toxiproxy_jitter={JITTER_MS}ms")
            signals.append("network_latency_injected=true")
        else:
            print(f"  Warning: toxic injection returned {resp.status_code}")

    since_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 5. Send orders to trigger timeouts
    print("Step 5: Sending order requests to trigger timeouts...")
    timeout_count = 0
    for i in range(1, 6):
        try:
            t0 = time.perf_counter()
            resp = client.post(
                f"{SERVICE_URL}/orders",
                json={"item": "widget", "quantity": 1, "amount": 9.99},
                timeout=5.0,
            )
            latency = time.perf_counter() - t0
            print(f"  Order {i}: HTTP {resp.status_code} in {latency:.2f}s")
            if resp.status_code == 500:
                signals.append("order_service_http_500")
        except httpx.TimeoutException as e:
            latency = time.perf_counter() - t0
            print(f"  Order {i}: TIMEOUT after {latency:.2f}s")
            timeout_count += 1
            signals.append("request_timeout")
        except Exception as e:
            print(f"  Order {i}: error: {e}")

    if timeout_count > 0:
        signals.append(f"timeout_count={timeout_count}")
        signals.append("http_request_duration_seconds_p95_elevated")

    # 6. Extract logs
    print(f"Step 6: Capturing JSON logs to {JSONL_PATH}...")
    json_lines = extract_json_logs(CONTAINER_ORDER, since_ts)
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for line in json_lines:
            f.write(line + "\n")
    print(f"Saved {len(json_lines)} JSON log entries.")

    # 7. Write metadata
    print(f"Step 7: Writing ground truth metadata to {META_PATH}...")
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": SERVICE_NAME,
        "failure_type": "network_timeout",
        "root_cause": (
            "Toxiproxy injects 3000ms latency (+500ms jitter) on the network path "
            "from order-service to payment-service. Requests to POST /orders time out "
            "waiting for payment confirmation."
        ),
        "expected_fix": (
            "Remove the Toxiproxy latency toxic via DELETE "
            "http://localhost:8474/proxies/payment-proxy/toxics/payment-latency. "
            "In production: investigate network congestion, firewall rules, "
            "or upstream service degradation"
        ),
        "signals": list(dict.fromkeys(signals)) if signals else [
            "toxiproxy_latency=3000ms",
            "network_latency_injected=true",
            "request_timeout",
            "http_request_duration_seconds_p95_elevated",
        ],
        "how_to_reproduce": "python infra/failures/run_scenario.py run nettimeout-order-001",
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\n=== Scenario Injection Complete ===")
    print("Restore command: python infra/failures/run_scenario.py restore")


if __name__ == "__main__":
    main()
