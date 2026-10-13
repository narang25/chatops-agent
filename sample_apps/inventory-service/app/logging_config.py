"""JSON structured logger — matches contracts/logs.md exactly."""
import json
import logging
import sys
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
    def format(self, record: logging.LogRecord) -> str:
        now = datetime.now(timezone.utc)
        log_entry: dict = {
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
            "service": self.service_name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra", None)
        if extra:
            log_entry["extra"] = extra
        return json.dumps(log_entry, default=str)

def setup_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter(service_name))
        logger.addHandler(handler)
    logger.propagate = False
    return logger
