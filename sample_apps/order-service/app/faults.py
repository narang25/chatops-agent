"""Runtime fault toggles for failure injection."""
import os
import random


class FaultToggles:
    def __init__(self):
        self.health_fail: bool = os.getenv("FAULT_HEALTH_FAIL", "").lower() == "true"
        self.slow_db: bool = os.getenv("FAULT_SLOW_DB", "").lower() == "true"
        self.db_error: bool = os.getenv("FAULT_DB_ERROR", "").lower() == "true"
        # FAULT_ERROR_RATE: float 0.0-1.0 — fraction of requests that return 500
        # Used for bad_deploy / high_error_rate scenario
        try:
            self.error_rate: float = float(os.getenv("FAULT_ERROR_RATE", "0"))
        except ValueError:
            self.error_rate = 0.0

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == "error_rate":
                    self.error_rate = float(value)
                else:
                    setattr(self, key, bool(value))

    def should_error(self) -> bool:
        """Return True with probability self.error_rate."""
        return self.error_rate > 0 and random.random() < self.error_rate

    def as_dict(self) -> dict:
        return {
            "health_fail": self.health_fail,
            "slow_db": self.slow_db,
            "db_error": self.db_error,
            "error_rate": self.error_rate,
        }


faults = FaultToggles()
