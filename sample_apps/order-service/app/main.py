"""
order-service — FastAPI microservice for order creation and management.

This service processes customer orders, interacts with payment-service via HTTP
for payment processing, and persists order records in PostgreSQL. Part of the
ChatOps Agent system used for monitoring, metrics scraping, and automated incident diagnosis.

Endpoints:
  GET  /health            Health check (returns 500 when health_fail fault is active)
  GET  /metrics           Prometheus exposition format (contracts/metrics.md)
  POST /orders            Create order (calls payment-service /pay, then stores in Postgres)
  GET  /orders/{order_id} Fetch order details by ID from Postgres
  POST /admin/fault       Toggle runtime fault injection flags

Required env vars:
  SERVICE_NAME          Must be 'order-service'
  DATABASE_URL          Postgres connection string
  PAYMENT_SERVICE_URL   Base URL for payment-service (e.g. http://payment-service:8000)

Optional env vars:
  LOG_LEVEL             Python logging level (default: INFO)
  FAULT_HEALTH_FAIL     Start with health check fault active (default: false)
  FAULT_SLOW_DB         Start with 3s database latency fault active (default: false)
  FAULT_DB_ERROR        Start with database exception fault active (default: false)
"""

import json
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
import psycopg2
import psutil
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from prometheus_client import CONTENT_TYPE_LATEST

from app.faults import faults
from app.logging_config import setup_logging
from app.metrics import (
    app_errors_total,
    app_memory_bytes,
    app_up,
    get_metrics_response,
    http_request_duration_seconds,
    http_requests_total,
)


# ---------------------------------------------------------------------------
# Helper: emit critical JSON log before logger is initialized
# ---------------------------------------------------------------------------
def _critical_exit(service: str, message: str) -> None:
    """Print contract-compliant JSON log to stdout and terminate process."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    log_payload = {
        "timestamp": ts,
        "service": service or "order-service",
        "level": "CRITICAL",
        "message": message,
    }
    print(json.dumps(log_payload, default=str), flush=True)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration: Validate required environment variables on startup
# ---------------------------------------------------------------------------
SERVICE_NAME = os.getenv("SERVICE_NAME", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not SERVICE_NAME:
    _critical_exit(
        service="order-service",
        message="SERVICE_NAME environment variable is required but not set",
    )

if not DATABASE_URL:
    _critical_exit(
        service=SERVICE_NAME,
        message="DATABASE_URL environment variable is required but not set",
    )

if not PAYMENT_SERVICE_URL:
    _critical_exit(
        service=SERVICE_NAME,
        message="PAYMENT_SERVICE_URL environment variable is required but not set",
    )

# Normalize URL to avoid double slashes when joining routes
PAYMENT_SERVICE_URL = PAYMENT_SERVICE_URL.rstrip("/")

# Initialize structured JSON logger conforming to contracts/logs.md
logger = setup_logging(SERVICE_NAME, LOG_LEVEL)


# ---------------------------------------------------------------------------
# Database Helpers
# ---------------------------------------------------------------------------
def _get_connection():
    """
    Return a psycopg2 database connection while respecting fault toggles.
    Simulates database latency (slow_db) or failures (db_error) when injected.
    """
    if faults.db_error:
        raise Exception("Simulated database error (db_error fault is ON)")
    if faults.slow_db:
        time.sleep(3)
    return psycopg2.connect(DATABASE_URL)


def _init_db() -> None:
    """
    Create the orders table if it does not already exist.
    Bypasses fault toggles to guarantee reliable schema initialization.
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id         SERIAL PRIMARY KEY,
            item       VARCHAR(100),
            quantity   INT,
            payment_id INT,
            status     VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# Background Thread: Update process memory gauge (RSS) every 5 seconds
# ---------------------------------------------------------------------------
def _memory_updater() -> None:
    """Periodically sample RSS memory in bytes and update Prometheus gauge."""
    while True:
        try:
            rss_bytes = psutil.Process().memory_info().rss
            app_memory_bytes.labels(service=SERVICE_NAME).set(rss_bytes)
        except Exception:
            pass
        time.sleep(5)


# ---------------------------------------------------------------------------
# Application Lifespan (Startup and Shutdown events)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set service health gauge to 1 (healthy/running)
    app_up.labels(service=SERVICE_NAME).set(1)
    logger.info("Service starting up")

    # Start memory updater in a background daemon thread
    mem_thread = threading.Thread(target=_memory_updater, daemon=True)
    mem_thread.start()

    # Retry DB connection up to 10 attempts (Postgres may still be initializing)
    for attempt in range(1, 11):
        try:
            _init_db()
            logger.info("Database initialised successfully")
            break
        except Exception as exc:
            logger.warning(
                f"DB init attempt {attempt}/10 failed: {exc}",
                extra={"attempt": attempt},
            )
            time.sleep(2)
    else:
        logger.error("Could not initialise database after 10 attempts")

    yield  # Application serves requests here

    # Mark service down upon shutdown
    app_up.labels(service=SERVICE_NAME).set(0)
    logger.info("Service shutting down")


# ---------------------------------------------------------------------------
# FastAPI Application Instance
# ---------------------------------------------------------------------------
app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


# ---------------------------------------------------------------------------
# Middleware: Track HTTP request counts and durations for Prometheus
# ---------------------------------------------------------------------------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # Exclude the metrics endpoint itself from instrumentation
    if request.url.path == "/metrics":
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    http_requests_total.labels(
        service=SERVICE_NAME,
        endpoint=request.url.path,
        status=str(response.status_code),
    ).inc()

    http_request_duration_seconds.labels(
        service=SERVICE_NAME,
        endpoint=request.url.path,
    ).observe(duration)

    return response


# ---------------------------------------------------------------------------
# Standard Endpoints: Health & Metrics
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """
    Health check endpoint.
    Returns 200 OK normally, or 500 Unhealthy if health_fail fault is toggled.
    """
    if faults.health_fail:
        app_up.labels(service=SERVICE_NAME).set(0)
        logger.warning("Health check failed (fault injected)")
        return JSONResponse(status_code=500, content={"status": "unhealthy"})
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """
    Prometheus exposition endpoint.
    Updates memory gauge right before producing scrape data for freshness.
    """
    try:
        app_memory_bytes.labels(service=SERVICE_NAME).set(
            psutil.Process().memory_info().rss
        )
    except Exception:
        pass
    return Response(content=get_metrics_response(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Order Domain Models & Endpoints
# ---------------------------------------------------------------------------
class OrderCreateRequest(BaseModel):
    item: str
    quantity: int
    amount: float


@app.post("/orders")
def create_order(order_req: OrderCreateRequest):
    """
    Create a new order:
    1. Call payment-service to process payment for the specified amount.
    2. If payment succeeds, persist order record with payment_id in Postgres.
    3. If payment-service is unreachable or fails, log ERROR and return 502 Bad Gateway.
    """
    pay_url = f"{PAYMENT_SERVICE_URL}/pay"

    # Step 1: Call payment-service synchronously with 5s timeout
    try:
        pay_resp = httpx.post(
            pay_url,
            json={"amount": order_req.amount},
            timeout=5.0,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        app_errors_total.labels(service=SERVICE_NAME).inc()
        logger.error(
            f"Payment service unreachable: {exc}",
            extra={"target": "payment-service"},
        )
        return JSONResponse(
            status_code=502,
            content={"error": f"Payment service unreachable: {exc}"},
        )
    except httpx.RequestError as exc:
        app_errors_total.labels(service=SERVICE_NAME).inc()
        logger.error(
            f"Payment service request failed: {exc}",
            extra={"target": "payment-service"},
        )
        return JSONResponse(
            status_code=502,
            content={"error": f"Payment service request failed: {exc}"},
        )

    # Step 2: Validate payment response status
    if pay_resp.status_code != 200:
        app_errors_total.labels(service=SERVICE_NAME).inc()
        logger.error(
            f"Payment service returned non-200 status: {pay_resp.status_code} body: {pay_resp.text}",
            extra={"target": "payment-service", "status_code": pay_resp.status_code},
        )
        return JSONResponse(
            status_code=502,
            content={
                "error": "Payment processing failed in payment-service",
                "status_code": pay_resp.status_code,
                "details": pay_resp.text,
            },
        )

    # Extract payment_id from payment response
    try:
        pay_data = pay_resp.json()
        payment_id = pay_data.get("payment_id")
    except Exception as exc:
        app_errors_total.labels(service=SERVICE_NAME).inc()
        logger.error(
            f"Failed to parse payment service response: {exc}",
            extra={"target": "payment-service"},
        )
        return JSONResponse(
            status_code=502,
            content={"error": "Invalid response received from payment-service"},
        )

    # Step 3: Insert order into database
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (item, quantity, payment_id, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (order_req.item, order_req.quantity, payment_id, "completed"),
        )
        row = cur.fetchone()
        order_id = row[0]
        created_at = row[1]
        conn.commit()
        cur.close()
        conn.close()

        logger.info(
            f"Order created: id={order_id} item={order_req.item} quantity={order_req.quantity} payment_id={payment_id}",
            extra={
                "order_id": order_id,
                "item": order_req.item,
                "quantity": order_req.quantity,
                "payment_id": payment_id,
                "amount": order_req.amount,
            },
        )

        return {
            "order_id": order_id,
            "item": order_req.item,
            "quantity": order_req.quantity,
            "payment_id": payment_id,
            "status": "completed",
            "created_at": str(created_at),
        }
    except Exception as exc:
        app_errors_total.labels(service=SERVICE_NAME).inc()
        logger.error(f"Failed to save order to database: {exc}")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    """
    Fetch an order record by ID from Postgres.
    Returns 404 if order does not exist, or 500 on database error.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, item, quantity, payment_id, status, created_at
            FROM orders
            WHERE id = %s
            """,
            (order_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row is None:
            logger.warning(
                f"Order not found: id={order_id}",
                extra={"order_id": order_id},
            )
            return JSONResponse(
                status_code=404,
                content={"error": f"Order {order_id} not found"},
            )

        order_data = {
            "order_id": row[0],
            "item": row[1],
            "quantity": row[2],
            "payment_id": row[3],
            "status": row[4],
            "created_at": str(row[5]),
        }
        logger.info(f"Order fetched: id={order_id}", extra={"order_id": order_id})
        return order_data
    except Exception as exc:
        app_errors_total.labels(service=SERVICE_NAME).inc()
        logger.error(f"Failed to fetch order {order_id}: {exc}")
        return JSONResponse(status_code=500, content={"error": str(exc)})


# ---------------------------------------------------------------------------
# Fault Injection Admin Endpoint
# ---------------------------------------------------------------------------
class FaultRequest(BaseModel):
    health_fail: bool | None = None
    slow_db: bool | None = None
    db_error: bool | None = None


@app.post("/admin/fault")
def set_faults(req: FaultRequest):
    """Toggle fault injection flags at runtime."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    faults.update(**updates)
    logger.info(f"Fault toggles updated: {updates}")
    return {"faults": faults.as_dict()}
