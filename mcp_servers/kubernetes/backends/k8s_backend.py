"""
Kubernetes runtime backend for the infra MCP server.

Implements the same RuntimeBackend interface as DockerBackend.
Selected when  RUNTIME=k8s  environment variable is set.

State mapping (Kubernetes → contract):
  Running          → running
  CrashLoopBackOff → restarting
  OOMKilled        → oom_killed
  Error            → exited
  Pending          → not_found  (not yet scheduled)
  Completed        → exited
  Unknown          → not_found

Requires: pip install kubernetes
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from .base import RuntimeBackend

try:
    from kubernetes import client as k8s_client  # type: ignore
    from kubernetes import config as k8s_config
    from kubernetes.client.rest import ApiException  # type: ignore

    _K8S_AVAILABLE = True
except ImportError:
    _K8S_AVAILABLE = False


# ── State / reason mapping ──────────────────────────────────────────────────

_WAITING_REASON_MAP: dict[str, str] = {
    "CrashLoopBackOff": "restarting",
    "OOMKilled": "oom_killed",
    "Error": "exited",
    "CreateContainerConfigError": "exited",
    "ImagePullBackOff": "not_found",
    "ErrImagePull": "not_found",
    "Pending": "not_found",
}

_PHASE_MAP: dict[str, str] = {
    "Running": "running",
    "Succeeded": "exited",
    "Failed": "exited",
    "Pending": "not_found",
    "Unknown": "not_found",
}

_HEALTH_MAP: dict[str | None, str | None] = {
    "True": "healthy",
    "False": "unhealthy",
    None: None,
}


def _to_contract_state(pod: Any) -> str:
    """Derive a contract state string from a k8s Pod object."""
    phase = (pod.status.phase or "Unknown") if pod.status else "Unknown"

    # Check container statuses first (more granular)
    container_statuses = (pod.status.container_statuses or []) if pod.status else []
    for cs in container_statuses:
        if cs.state:
            if cs.state.waiting and cs.state.waiting.reason:
                mapped = _WAITING_REASON_MAP.get(cs.state.waiting.reason)
                if mapped:
                    return mapped
            if cs.state.terminated:
                term = cs.state.terminated
                if term.reason == "OOMKilled":
                    return "oom_killed"
                return "exited"

    return _PHASE_MAP.get(phase, "not_found")


def _get_condition_ready(pod: Any) -> str | None:
    """Return 'True'/'False'/None from the Ready condition."""
    conditions = (pod.status.conditions or []) if pod.status else []
    for cond in conditions:
        if cond.type == "Ready":
            return cond.status  # "True" or "False"
    return None


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


class K8sBackend(RuntimeBackend):
    """Kubernetes backend using the official Python client."""

    def __init__(self, namespace: str | None = None) -> None:
        if not _K8S_AVAILABLE:
            raise ImportError(
                "The 'kubernetes' package is not installed. "
                "Run: pip install kubernetes"
            )
        self.namespace = namespace or os.environ.get("K8S_NAMESPACE", "chatops")
        # Load config from in-cluster env or kubeconfig file
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        self._core: k8s_client.CoreV1Api = k8s_client.CoreV1Api()
        self._apps: k8s_client.AppsV1Api = k8s_client.AppsV1Api()

    # ── helpers ─────────────────────────────────────────────────────────────

    def _find_pod(self, service: str) -> Any | None:
        """Return the most recent pod for the given service label selector."""
        try:
            pods = self._core.list_namespaced_pod(
                self.namespace,
                label_selector=f"app={service}",
            )
        except ApiException:
            return None
        items = pods.items or []
        if not items:
            return None
        # Return the most recently created pod
        return max(items, key=lambda p: p.metadata.creation_timestamp or datetime.min)

    def _memory_limit_mb(self, pod: Any) -> float | None:
        specs = (pod.spec.containers or []) if pod.spec else []
        for cs in specs:
            if cs.resources and cs.resources.limits:
                mem = cs.resources.limits.get("memory")
                if mem:
                    # Parse k8s memory strings: 128Mi, 1Gi, etc.
                    return _parse_memory_mb(mem)
        return None

    def _restart_count(self, pod: Any) -> int:
        container_statuses = (pod.status.container_statuses or []) if pod.status else []
        return sum(cs.restart_count or 0 for cs in container_statuses)

    def _oom_killed(self, pod: Any) -> bool:
        container_statuses = (pod.status.container_statuses or []) if pod.status else []
        for cs in container_statuses:
            if cs.last_state and cs.last_state.terminated:
                if cs.last_state.terminated.reason == "OOMKilled":
                    return True
            if cs.state and cs.state.terminated:
                if cs.state.terminated.reason == "OOMKilled":
                    return True
        return False

    def _exit_code(self, pod: Any) -> int | None:
        container_statuses = (pod.status.container_statuses or []) if pod.status else []
        for cs in container_statuses:
            if cs.state and cs.state.terminated:
                return cs.state.terminated.exit_code
            if cs.last_state and cs.last_state.terminated:
                return cs.last_state.terminated.exit_code
        return None

    # ── RuntimeBackend interface ─────────────────────────────────────────────

    def get_pod_status(self, service: str) -> dict:
        pod = self._find_pod(service)
        if pod is None:
            return {
                "service": service,
                "state": "not_found",
                "restart_count": 0,
                "exit_code": None,
                "oom_killed": False,
                "health": None,
                "started_at": None,
                "memory_limit_mb": None,
            }

        state = _to_contract_state(pod)
        ready_condition = _get_condition_ready(pod)
        health = _HEALTH_MAP.get(ready_condition)

        started_at = None
        statuses = (pod.status.container_statuses or []) if pod.status else []
        for cs in statuses:
            if cs.state and cs.state.running:
                started_at = _iso(cs.state.running.started_at)
                break

        return {
            "service": service,
            "state": state,
            "restart_count": self._restart_count(pod),
            "exit_code": self._exit_code(pod),
            "oom_killed": self._oom_killed(pod),
            "health": health,
            "started_at": started_at,
            "memory_limit_mb": self._memory_limit_mb(pod),
        }

    def get_events(self, service: str, minutes: int = 5) -> dict:
        try:
            events_list = self._core.list_namespaced_event(
                self.namespace,
                field_selector=f"involvedObject.name={service}",
            )
        except ApiException as exc:
            return {"service": service, "events": [], "error": str(exc)}

        cutoff = datetime.now(tz=UTC).timestamp() - minutes * 60
        mapped: list[dict] = []

        for ev in events_list.items or []:
            ts_obj = ev.last_timestamp or ev.event_time
            if ts_obj is None:
                continue
            ts = ts_obj.timestamp() if hasattr(ts_obj, "timestamp") else 0
            if ts < cutoff:
                continue

            reason = (ev.reason or "").lower()
            event_type = "info"
            if reason in ("oom", "oomkilling", "backoff"):
                event_type = "oom"
            elif reason in ("killing", "failed", "unhealthy", "backoff"):
                event_type = "error"
            elif reason in ("started", "pulled", "created"):
                event_type = "start"

            mapped.append({
                "timestamp": _iso(ts_obj) or "",
                "type": event_type,
                "reason": ev.reason or "",
                "message": ev.message or "",
                "count": ev.count or 1,
            })

        return {"service": service, "events": sorted(mapped, key=lambda e: e["timestamp"])}

    def get_logs(
        self,
        service: str,
        minutes: int = 10,
        level: str | None = None,
        limit: int = 100,
    ) -> dict:
        import json as _json

        pod = self._find_pod(service)
        if pod is None:
            return {"service": service, "count": 0, "lines": [], "error": "pod not found"}

        pod_name = pod.metadata.name
        since_seconds = minutes * 60

        try:
            raw: str = self._core.read_namespaced_pod_log(
                pod_name,
                self.namespace,
                tail_lines=limit * 3,  # fetch extra; we'll filter
                since_seconds=since_seconds,
            )
        except ApiException as exc:
            return {"service": service, "count": 0, "lines": [], "error": str(exc)}

        lines: list[dict] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
            except _json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            # Filter by level if requested
            if level and obj.get("level", "").lower() != level.lower():
                continue
            lines.append({
                "timestamp": obj.get("timestamp") or obj.get("time") or "",
                "level": obj.get("level") or "info",
                "message": obj.get("message") or obj.get("msg") or "",
            })
            if len(lines) >= limit:
                break

        return {"service": service, "count": len(lines), "lines": lines}

    def list_services(self) -> dict:
        try:
            deps = self._apps.list_namespaced_deployment(self.namespace)
        except ApiException as exc:
            return {"services": [], "error": str(exc)}

        services: list[dict] = []
        for dep in deps.items or []:
            name = dep.metadata.name
            # Map deployment ready replicas → state
            ready = dep.status.ready_replicas or 0 if dep.status else 0
            desired = dep.spec.replicas or 1 if dep.spec else 1
            state = "running" if ready >= desired else ("restarting" if ready > 0 else "exited")
            services.append({"name": name, "state": state})

        return {"services": services}


# ── Utility ─────────────────────────────────────────────────────────────────

def _parse_memory_mb(mem_str: str) -> float:
    """Parse Kubernetes memory string (128Mi, 1Gi, 512M) → MB."""
    mem_str = mem_str.strip()
    multipliers = {
        "Ki": 1 / 1024,
        "Mi": 1.0,
        "Gi": 1024.0,
        "K": 1 / 1024,
        "M": 1.0,
        "G": 1024.0,
    }
    for suffix, factor in multipliers.items():
        if mem_str.endswith(suffix):
            try:
                return float(mem_str[: -len(suffix)]) * factor
            except ValueError:
                return 0.0
    try:
        # Assume bytes
        return float(mem_str) / (1024 * 1024)
    except ValueError:
        return 0.0
