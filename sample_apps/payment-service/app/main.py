"""
payment-service — FastAPI microservice that accepts payments via Postgres.

Endpoints:
  GET  /health        Health check (returns 500 when health_fail fault is on)
  GET  /metrics       Prometheus metrics (contracts/metrics.md)
  POST /pay           Create a payment record
  GET  /leak          Allocate ~10 MB that is never freed (OOM testing)
  GET  /burn          Busy-loop to burn CPU (CPU saturation testing)
  POST /admin/fault   Toggle runtime faults

Required env vars:  SERVICE_NAME, DATABASE_URL
Optional env vars:  LOG_LEVEL (default INFO), FAULT_HEALTH_FAIL, FAULT_SLOW_DB, FAULT_DB_ERROR
"""

import os
import sys
import time
import threading
from contextlib import asynccontextmanager

import psutil
import psycopg2
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from prometheus_client import CONTENT_TYPE_LATEST

from app.logging_config import setup_logging
from app.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    app_errors_total,
    app_memory_bytes,
    app_up,
    get_metrics_response,
)
from app.faults import faults

# ---------------------------------------------------------------------------
# Configuration (validate required env vars early)
# ---------------------------------------------------------------------------
SERVICE_NAME = os.getenv("SERVICE_NAME", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not SERVICE_NAME:
    # Can't use the JSON logger yet, so write a contract-shaped line manually
    import json
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    print(
        json.dumps(
            {
                "timestamp": ts,
                "service": "payment-service",
                "level": "CRITICAL",
                "message": "SERVICE_NAME environment variable is required but not set",
            }
        ),
        flush=True,
    )
    sys.exit(1)

if not DATABASE_URL:
    import json
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    print(
        json.dumps(
            {
                "timestamp": ts,
                "service": SERVICE_NAME,
                "level": "CRITICAL",
                "message": "DATABASE_URL environment variable is required but not set",
            }
        ),
        flush=True,
    )
    sys.exit(1)

logger = setup_logging(SERVICE_NAME, LOG_LEVEL)

# ---------------------------------------------------------------------------
# Memory leak storage (for /leak endpoint — never freed)
# ---------------------------------------------------------------------------
_leaked_chunks: list[bytearray] = []

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_connection():
    """Return a psycopg2 connection, respecting fault toggles."""
    if faults.db_error:
        raise Exception("Simulated database error (db_error fault is ON)")
    if faults.slow_db:
        time.sleep(3)
    return psycopg2.connect(DATABASE_URL)


def _init_db() -> None:
    """Create tables if they don't exist. Called on startup with retries."""
    conn = psycopg2.connect(DATABASE_URL)  # bypass fault toggles for init
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id         SERIAL PRIMARY KEY,
            amount     DECIMAL(10, 2) NOT NULL,
            status     VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# Background thread: update memory gauge every 5 seconds
# ---------------------------------------------------------------------------

def _memory_updater() -> None:
    while True:
        try:
            app_memory_bytes.labels(service=SERVICE_NAME).set(
                psutil.Process().memory_info().rss
            )
        except Exception:
            pass
        time.sleep(5)


# ---------------------------------------------------------------------------
# App lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mark service as up
    app_up.labels(service=SERVICE_NAME).set(1)
    logger.info("Service starting up")

    # Start background memory metric updater
    mem_thread = threading.Thread(target=_memory_updater, daemon=True)
    mem_thread.start()

    # Initialise DB with retries (Postgres may not be ready yet in Docker)
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

    yield  # ---- app is running ----

    app_up.labels(service=SERVICE_NAME).set(0)
    logger.info("Service shutting down")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


# ---------------------------------------------------------------------------
# Middleware — track request count and latency for every endpoint
# ---------------------------------------------------------------------------

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # Don't instrument the /metrics endpoint itself
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

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
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Health check. Returns 500 when the health_fail fault is active."""
    if faults.health_fail:
        app_up.labels(service=SERVICE_NAME).set(0)
        logger.warning("Health check failed (fault injected)")
        return JSONResponse(status_code=500, content={"status": "unhealthy"})
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    # Update memory right before scrape for freshness
    try:
        app_memory_bytes.labels(service=SERVICE_NAME).set(
            psutil.Process().memory_info().rss
        )
    except Exception:
        pass
    return Response(content=get_metrics_response(), media_type=CONTENT_TYPE_LATEST)


# -- Payment endpoints -----------------------------------------------------

class PaymentRequest(BaseModel):
    amount: float


@app.post("/pay")
def create_payment(payment: PaymentRequest):
    """Create a payment record in Postgres."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO payments (amount, status) VALUES (%s, %s) RETURNING id",
            (payment.amount, "completed"),
        )
        payment_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        logger.info(
            f"Payment created: id={payment_id} amount={payment.amount}",
            extra={"payment_id": payment_id, "amount": payment.amount},
        )
        return {
            "payment_id": payment_id,
            "status": "completed",
            "amount": payment.amount,
        }
    except Exception as exc:
        app_errors_total.labels(service=SERVICE_NAME).inc()
        logger.error(f"Payment failed: {exc}")
        return JSONResponse(status_code=500, content={"error": str(exc)})


# -- OOM leak endpoint (payment-service only) ------------------------------

@app.get("/leak")
def leak_memory():
    """Allocate ~10 MB of memory that is never freed. Used for OOM testing."""
    chunk = bytearray(10 * 1024 * 1024)  # 10 MB
    _leaked_chunks.append(chunk)
    total_mb = len(_leaked_chunks) * 10
    logger.warning(
        f"Memory leak: allocated 10 MB, total leaked: {total_mb} MB",
        extra={"leaked_mb": total_mb, "chunks": len(_leaked_chunks)},
    )
    return {"leaked_mb": total_mb, "chunks": len(_leaked_chunks)}


# -- CPU burn endpoint (payment-service only) ------------------------------

@app.get("/burn")
def burn_cpu(duration_ms: int = 500):
    """Busy-loop to burn CPU for specified duration (in ms). Used for cpu_saturation testing."""
    start = time.perf_counter()
    while (time.perf_counter() - start) * 1000 < duration_ms:
        _ = 3.14159 ** 2.71828
    logger.warning(
        f"CPU burn completed: {duration_ms}ms",
        extra={"duration_ms": duration_ms},
    )
    return {"burned_ms": duration_ms}


# -- Fault injection admin endpoint ----------------------------------------

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
