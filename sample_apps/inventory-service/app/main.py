"""
inventory-service — FastAPI microservice for stock management backed by Postgres.

Endpoints:
  GET  /health        Health check (returns 500 when health_fail fault is on)
  GET  /metrics       Prometheus metrics (contracts/metrics.md)
  GET  /stock/{item}  Look up stock quantity for an item
  POST /stock/{item}  Update stock quantity for an item
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
                "service": "inventory-service",
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
    """Create tables if they don't exist and seed initial inventory data.

    Called during application lifespan startup with retries.
    """
    conn = psycopg2.connect(DATABASE_URL)  # bypass fault toggles for init
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id         SERIAL PRIMARY KEY,
            item       VARCHAR(100) UNIQUE NOT NULL,
            quantity   INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Seed default sample stock items if not present
    cur.execute(
        """
        INSERT INTO inventory (item, quantity)
        VALUES ('widget', 100), ('gadget', 50), ('doohickey', 200)
        ON CONFLICT (item) DO NOTHING
        """
    )
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# Background thread: update memory gauge every 5 seconds
# ---------------------------------------------------------------------------

def _memory_updater() -> None:
    """Periodically sample process RSS memory and record into Prometheus gauge."""
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

    # Initialise DB with retries (Postgres may not be ready immediately in Docker)
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


# -- Stock inventory endpoints ---------------------------------------------

class UpdateStockRequest(BaseModel):
    quantity: int


@app.get("/stock/{item}")
def get_stock(item: str):
    """Look up item stock quantity in the inventory table."""
    logger.info(f"Checking stock for item: {item}", extra={"item": item})
    conn = None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT item, quantity FROM inventory WHERE item = %s",
            (item,),
        )
        row = cur.fetchone()
        cur.close()

        if row is None:
            logger.warning(f"Item not found: {item}", extra={"item": item})
            return JSONResponse(
                status_code=404,
                content={"error": f"Item not found: {item}"},
            )

        item_name, quantity = row[0], row[1]
        logger.info(
            f"Stock retrieved: item={item_name} quantity={quantity}",
            extra={"item": item_name, "quantity": quantity},
        )
        return {"item": item_name, "quantity": quantity}
    except Exception as exc:
        app_errors_total.labels(service=SERVICE_NAME).inc()
        logger.error(f"Stock lookup failed: {exc}", extra={"item": item})
        return JSONResponse(status_code=500, content={"error": str(exc)})
    finally:
        if conn:
            conn.close()


@app.post("/stock/{item}")
def update_stock(item: str, payload: UpdateStockRequest):
    """Update stock quantity for an item in the inventory table."""
    logger.info(
        f"Updating stock for item: {item} quantity={payload.quantity}",
        extra={"item": item, "quantity": payload.quantity},
    )
    conn = None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE inventory
            SET quantity = %s, updated_at = CURRENT_TIMESTAMP
            WHERE item = %s
            RETURNING item, quantity
            """,
            (payload.quantity, item),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()

        if row is None:
            logger.warning(f"Item not found for update: {item}", extra={"item": item})
            return JSONResponse(
                status_code=404,
                content={"error": f"Item not found: {item}"},
            )

        item_name, quantity = row[0], row[1]
        logger.info(
            f"Stock updated: item={item_name} quantity={quantity}",
            extra={"item": item_name, "quantity": quantity},
        )
        return {"item": item_name, "quantity": quantity}
    except Exception as exc:
        if conn:
            conn.rollback()
        app_errors_total.labels(service=SERVICE_NAME).inc()
        logger.error(f"Stock update failed: {exc}", extra={"item": item})
        return JSONResponse(status_code=500, content={"error": str(exc)})
    finally:
        if conn:
            conn.close()


# -- Fault injection admin endpoint ----------------------------------------

class FaultRequest(BaseModel):
    health_fail: bool | None = None
    slow_db: bool | None = None
    db_error: bool | None = None


@app.post("/admin/fault")
def set_faults(req: FaultRequest):
    """Toggle runtime fault injection flags."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    faults.update(**updates)
    logger.info(f"Fault toggles updated: {updates}")
    return {"faults": faults.as_dict()}
