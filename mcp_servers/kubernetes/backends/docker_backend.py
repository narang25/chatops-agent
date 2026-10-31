"""
Docker SDK implementation of RuntimeBackend.
Queries local Docker daemon for container state, events, and JSON logs.
"""

import json
import time
from datetime import UTC, datetime
from typing import Any

import docker
from docker.errors import DockerException

from mcp_servers.kubernetes.backends.base import RuntimeBackend

REGISTERED_SERVICES = ["payment-service", "order-service", "inventory-service"]


class DockerBackend(RuntimeBackend):
    def __init__(self):
        try:
            self.client = docker.from_env()
        except DockerException as e:
            self.client = None
            self._init_error = str(e)
        else:
            self._init_error = None

    def _find_container(self, service: str):
        """Find container matching service name or compose naming convention."""
        if not self.client:
            raise RuntimeError(f"Docker client not initialized: {self._init_error}")

        containers = self.client.containers.list(all=True)
        for c in containers:
            name = c.name.lstrip("/")
            # Match exact name (e.g. payment-service) or compose prefix/suffix
            if name == service or name.startswith(f"{service}-") or f"-{service}-" in name or name.endswith(f"-{service}"):
                return c
        return None

    def get_pod_status(self, service: str) -> dict[str, Any]:
        try:
            container = self._find_container(service)
        except Exception as exc:
            return {"error": f"Docker lookup failed for {service}: {exc}"}

        if not container:
            return {
                "service": service,
                "state": "not_found",
                "restart_count": 0,
                "exit_code": None,
                "oom_killed": False,
                "health": "none",
                "started_at": None,
                "memory_limit_mb": None,
            }

        try:
            container.reload()
            attrs = container.attrs
            state_raw = attrs.get("State", {})
            raw_status = state_raw.get("Status", "").lower()
            oom_killed = bool(state_raw.get("OOMKilled", False))
            exit_code = state_raw.get("ExitCode")
            restart_count = int(attrs.get("RestartCount", 0))
            started_at = state_raw.get("StartedAt")

            health_info = state_raw.get("Health", {})
            health_status = health_info.get("Status", "").lower() if health_info else "none"
            if health_status not in {"healthy", "unhealthy"}:
                health_status = "none"

            mem_limit = attrs.get("HostConfig", {}).get("Memory", 0)
            memory_limit_mb = int(mem_limit / (1024 * 1024)) if mem_limit > 0 else None

            # Map to contract states: running|restarting|exited|oom_killed|unhealthy|not_found
            if health_status == "unhealthy":
                state = "unhealthy"
            elif oom_killed or exit_code == 137:
                state = "oom_killed"
            elif raw_status == "restarting":
                state = "restarting"
            elif raw_status == "exited":
                state = "exited"
            elif raw_status == "running":
                state = "running"
            else:
                state = raw_status

            return {
                "service": service,
                "state": state,
                "restart_count": restart_count,
                "exit_code": exit_code,
                "oom_killed": oom_killed or (exit_code == 137),
                "health": health_status,
                "started_at": started_at,
                "memory_limit_mb": memory_limit_mb,
            }
        except Exception as exc:
            return {"error": f"Failed reading status for {service}: {exc}"}

    def get_events(self, service: str, minutes: int = 15) -> dict[str, Any]:
        try:
            container = self._find_container(service)
        except Exception as exc:
            return {"error": f"Docker lookup failed for {service}: {exc}"}

        if not container:
            return {"service": service, "events": []}

        now_ts = int(time.time())
        since_ts = now_ts - (minutes * 60)
        events_list = []

        try:
            # Query Docker events filtered by container
            docker_events = self.client.events(
                since=since_ts,
                until=now_ts,
                filters={"container": container.id},
                decode=True,
            )
            for ev in docker_events:
                action = ev.get("Action", "unknown")
                timestamp_s = ev.get("time", now_ts)
                iso_ts = datetime.fromtimestamp(timestamp_s, UTC).isoformat(timespec="seconds")
                is_warning = action in {"die", "oom", "kill", "health_status: unhealthy"}
                events_list.append(
                    {
                        "timestamp": iso_ts,
                        "type": "Warning" if is_warning else "Normal",
                        "reason": action.capitalize(),
                        "message": f"Container {service} action: {action}",
                    }
                )
        except Exception:
            # If streaming daemon events fails or times out, fall back to current container status event
            pass

        # If no events found in window, report current state event
        if not events_list:
            st = self.get_pod_status(service)
            started_at = st.get("started_at") or datetime.now(UTC).isoformat(timespec="seconds")
            events_list.append(
                {
                    "timestamp": started_at,
                    "type": "Normal" if st.get("state") == "running" else "Warning",
                    "reason": "StateReport",
                    "message": f"Container {service} is currently {st.get('state')}.",
                }
            )

        return {"service": service, "events": events_list}

    def get_logs(
        self,
        service: str,
        minutes: int = 10,
        level: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        try:
            container = self._find_container(service)
        except Exception as exc:
            return {"error": f"Docker lookup failed for {service}: {exc}"}

        if not container:
            return {"service": service, "count": 0, "lines": []}

        now_ts = int(time.time())
        since_ts = now_ts - (minutes * 60)

        try:
            raw_bytes = container.logs(since=since_ts, timestamps=False)
            raw_text = raw_bytes.decode("utf-8", errors="replace")
        except Exception as exc:
            return {"error": f"Failed reading logs for {service}: {exc}"}

        matched_lines = []
        target_level = level.upper() if level else None

        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict) and "timestamp" in parsed and "level" in parsed:
                    msg_level = str(parsed.get("level", "")).upper()
                    if target_level is None or msg_level == target_level:
                        matched_lines.append(
                            {
                                "timestamp": parsed.get("timestamp", ""),
                                "level": msg_level,
                                "message": parsed.get("message", ""),
                            }
                        )
            except Exception:
                continue

        # Limit output
        if limit and limit > 0:
            matched_lines = matched_lines[-limit:]

        return {
            "service": service,
            "count": len(matched_lines),
            "lines": matched_lines,
        }

    def list_services(self) -> dict[str, Any]:
        services_status = []
        for svc in REGISTERED_SERVICES:
            st = self.get_pod_status(svc)
            services_status.append(
                {
                    "name": svc,
                    "state": st.get("state", "unknown"),
                }
            )
        return {"services": services_status}
