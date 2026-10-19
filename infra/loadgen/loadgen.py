"""
Lightweight traffic generator for ChatOps microservices.
Sends requests steadily (1-2 req/s) across payment-service, order-service,
and inventory-service so Prometheus and Grafana dashboards display live data.
"""

import os
import random
import time
import httpx

PAYMENT_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8000")
ORDER_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8000")
INVENTORY_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:8000")

ITEMS = ["widget", "gadget", "doohickey"]

def send_traffic():
    # Wait for services to be ready
    print("Load generator waiting 5 seconds for services to warm up...", flush=True)
    time.sleep(5)
    print("Load generator starting traffic loop...", flush=True)

    client = httpx.Client(timeout=3.0)

    while True:
        try:
            action = random.choice(["health", "stock", "order", "pay"])

            if action == "health":
                client.get(f"{PAYMENT_URL}/health")
                client.get(f"{ORDER_URL}/health")
                client.get(f"{INVENTORY_URL}/health")

            elif action == "stock":
                item = random.choice(ITEMS)
                client.get(f"{INVENTORY_URL}/stock/{item}")

            elif action == "order":
                item = random.choice(ITEMS)
                client.post(
                    f"{ORDER_URL}/orders",
                    json={
                        "item": item,
                        "quantity": random.randint(1, 5),
                        "amount": round(random.uniform(10.0, 100.0), 2)
                    }
                )

            elif action == "pay":
                client.post(
                    f"{PAYMENT_URL}/pay",
                    json={"amount": round(random.uniform(5.0, 50.0), 2)}
                )

        except Exception as e:
            # Expected during failure injections or cold starts
            pass

        # Sleep between 0.5 and 1.5 seconds to generate ~1-2 req/s
        time.sleep(random.uniform(0.5, 1.2))

if __name__ == "__main__":
    send_traffic()
