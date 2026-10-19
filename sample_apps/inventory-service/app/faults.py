"""Runtime fault toggles for failure injection."""
import os

class FaultToggles:
    def __init__(self):
        self.health_fail: bool = os.getenv("FAULT_HEALTH_FAIL", "").lower() == "true"
        self.slow_db: bool = os.getenv("FAULT_SLOW_DB", "").lower() == "true"
        self.db_error: bool = os.getenv("FAULT_DB_ERROR", "").lower() == "true"
    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, bool(value))
    def as_dict(self) -> dict:
        return {"health_fail": self.health_fail, "slow_db": self.slow_db, "db_error": self.db_error}

faults = FaultToggles()
