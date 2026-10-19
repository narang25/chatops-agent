"""
Runtime fault toggles for failure injection.

Controllable two ways:
  1. Environment variables at startup:  FAULT_HEALTH_FAIL=true
  2. HTTP at runtime:  POST /admin/fault  {"health_fail": true}

Keeps it minimal: three boolean flags that the route handlers check.
"""

import os


class FaultToggles:
    """Mutable container for fault injection flags."""

    def __init__(self):
        self.health_fail: bool = os.getenv("FAULT_HEALTH_FAIL", "").lower() == "true"
        self.slow_db: bool = os.getenv("FAULT_SLOW_DB", "").lower() == "true"
        self.db_error: bool = os.getenv("FAULT_DB_ERROR", "").lower() == "true"

    def update(self, **kwargs) -> None:
        """Update one or more toggles. Unknown keys are silently ignored."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, bool(value))

    def as_dict(self) -> dict:
        return {
            "health_fail": self.health_fail,
            "slow_db": self.slow_db,
            "db_error": self.db_error,
        }


# Singleton used across the app
faults = FaultToggles()
