"""
JSON structured logger — matches contracts/logs.md exactly.

Output format (one JSON object per line to stdout):
  {"timestamp": "2026-10-12T10:15:30.123Z", "service": "payment-service",
   "level": "ERROR", "message": "...", "extra": {...}}
"""

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON matching the project contract."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        now = datetime.now(timezone.utc)
        log_entry: dict = {
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.")
            + f"{now.microsecond // 1000:03d}Z",
            "service": self.service_name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Attach optional extra fields if the caller passed them
        extra = getattr(record, "extra", None)
        if extra:
            log_entry["extra"] = extra
        return json.dumps(log_entry, default=str)


def setup_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """Create and return a JSON logger that writes to stdout."""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid adding duplicate handlers if called twice
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter(service_name))
        logger.addHandler(handler)

    logger.propagate = False
    return logger
