"""
Evidence-First Code Gate (Task T2).
====================================
Enforces that the ChatOps agent inspects live telemetry (pod status and logs)
before consulting the runbook knowledge base via `search_runbooks`.

Gate Rules:
1. If the query names a specific service (or if a service was targeted in recent calls),
   the current run's tool trace MUST contain at least:
     - `get_pod_status` for that service
     - `get_logs` for that service
   Otherwise, search_runbooks returns:
     {"error": "gather evidence first: inspect pod status and logs for <service> before consulting runbooks"}
2. For questions that name no service, the trace MUST contain at least `list_services`
   (or pod status for any service).
   Otherwise, search_runbooks returns:
     {"error": "gather evidence first: call list_services to discover active services before consulting runbooks"}
"""

from __future__ import annotations

import re
import threading
from typing import Any

KNOWN_SERVICES = {"payment-service", "order-service", "inventory-service"}
SERVICE_ALIASES = {
    "payment": "payment-service",
    "order": "order-service",
    "inventory": "inventory-service",
}

STATUS_TOOLS = {
    "get_pod_status",
    "live_get_pod_status",
    "stub_get_pod_status",
}

LOG_TOOLS = {
    "get_logs",
    "live_get_logs",
    "stub_get_logs",
}

LIST_TOOLS = {
    "list_services",
    "live_list_services",
    "stub_list_services",
}


class EvidenceTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._trace: list[dict[str, Any]] = []

    def reset(self) -> None:
        """Reset the tool trace for a new run/session."""
        with self._lock:
            self._trace.clear()

    def record(self, tool_name: str, **kwargs: Any) -> None:
        """Record a tool execution in the current run's trace."""
        with self._lock:
            self._trace.append({"tool": tool_name, "args": kwargs})

    def get_trace(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._trace)

    def extract_target_service(self, query: str) -> str | None:
        """Extract a service name from the query text or recent trace calls."""
        q_lower = query.lower()
        for svc in KNOWN_SERVICES:
            if svc in q_lower:
                return svc
        for alias, full_svc in SERVICE_ALIASES.items():
            # Match whole word alias (e.g. \bpayment\b)
            if re.search(rf"\b{alias}\b", q_lower):
                return full_svc

        # Fallback: inspect the most recent service targeted in trace
        with self._lock:
            for item in reversed(self._trace):
                svc = item.get("args", {}).get("service")
                if svc and svc in KNOWN_SERVICES:
                    return svc
        return None

    def check_gate(self, query: str) -> dict[str, str] | None:
        """
        Verify that evidence has been gathered.
        Returns None if gate passes, or an error dict if blocked.
        """
        with self._lock:
            trace = list(self._trace)

        target_service = self.extract_target_service(query)

        if target_service:
            has_status = any(
                item["tool"] in STATUS_TOOLS
                and item.get("args", {}).get("service") == target_service
                for item in trace
            )
            has_logs = any(
                item["tool"] in LOG_TOOLS
                and item.get("args", {}).get("service") == target_service
                for item in trace
            )

            if not (has_status and has_logs):
                missing = []
                if not has_status:
                    missing.append(f"get_pod_status for {target_service}")
                if not has_logs:
                    missing.append(f"get_logs for {target_service}")
                return {
                    "error": (
                        f"gather evidence first: inspect pod status and logs for {target_service} "
                        f"before consulting runbooks (missing: {', '.join(missing)})"
                    )
                }
        else:
            # Query names no service: require list_services or any pod status first
            has_list = any(item["tool"] in LIST_TOOLS for item in trace)
            has_any_status = any(item["tool"] in STATUS_TOOLS for item in trace)

            if not (has_list or has_any_status):
                return {
                    "error": "gather evidence first: call list_services to discover active services before consulting runbooks"
                }

        return None


# Global singleton instance for the process
_TRACKER = EvidenceTracker()

record_evidence = _TRACKER.record
reset_evidence = _TRACKER.reset
get_evidence_trace = _TRACKER.get_trace
check_evidence_gate = _TRACKER.check_gate

