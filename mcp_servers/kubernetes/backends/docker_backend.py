"""
Docker SDK implementation of RuntimeBackend.
Queries local Docker daemon for container state, events, JSON logs, and system changes.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, NotFound
import httpx

from mcp_servers.kubernetes.backends.base import RuntimeBackend

REGISTERED_SERVICES = ["payment-service", "order-service", "inventory-service"]
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEPLOY_LOG_PATH = PROJECT_ROOT / "data" / "deploy_events.jsonl"


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
            state_info = container.attrs.get("State", {})
            host_config = container.attrs.get("HostConfig", {})
            status = state_info.get("Status", "").lower()
            exit_code = state_info.get("ExitCode")
            oom_killed = bool(state_info.get("OOMKilled", False))
            restarts = int(container.attrs.get("RestartCount", 0))
            started_at = state_info.get("StartedAt")

            # Memory limit
            mem_bytes = host_config.get("Memory", 0)
            mem_limit_mb = int(mem_bytes / (1024 * 1024)) if mem_bytes > 0 else None

            # Health
            health_info = state_info.get("Health", {})
            health_str = health_info.get("Status", "none").lower()
            if health_str not in ["healthy", "unhealthy"]:
                health_str = "none"

            # Derive contract state
            if oom_killed:
                state = "oom_killed"
            elif status == "restarting":
                state = "restarting"
            elif health_str == "unhealthy":
                state = "unhealthy"
            elif status == "running":
                state = "running"
            elif status in ["exited", "dead"]:
                state = "exited"
            else:
                state = "not_found"

            return {
                "service": service,
                "state": state,
                "restart_count": restarts,
                "exit_code": exit_code,
                "oom_killed": oom_killed,
                "health": health_str,
                "started_at": started_at,
                "memory_limit_mb": mem_limit_mb,
            }
        except Exception as exc:
            return {"error": f"Error inspecting {service}: {exc}"}

    def get_events(self, service: str, minutes: int = 15) -> dict[str, Any]:
        if not self.client:
            return {"error": f"Docker client not initialized: {self._init_error}"}

        try:
            container = self._find_container(service)
        except Exception as exc:
            return {"error": f"Docker container lookup failed for {service}: {exc}"}

        if not container:
            return {"service": service, "events": []}

        now_ts = int(time.time())
        since_ts = now_ts - (minutes * 60)

        events_list = []
        try:
            # Query docker events API for container
            filters = {"container": container.id}
            raw_events = self.client.events(since=since_ts, until=now_ts, filters=filters, decode=True)

            for ev in raw_events:
                action = ev.get("Action", "")
                actor_attrs = ev.get("Actor", {}).get("Attributes", {})
                time_epoch = ev.get("time", 0)
                ts_str = datetime.fromtimestamp(time_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                ev_type = "info"
                reason = action
                msg = f"Container action {action}"

                if action in ["oom", "die"]:
                    exit_code = actor_attrs.get("exitCode")
                    if action == "oom" or exit_code == "137":
                        ev_type = "oom"
                        reason = "OOMKilled"
                        msg = "Container terminated due to out-of-memory"
                    else:
                        ev_type = "die"
                        reason = f"ExitCode_{exit_code}"
                        msg = f"Container died with exit code {exit_code}"
                elif action == "restart":
                    ev_type = "restart"
                    reason = "Restart"
                    msg = "Container restarted by daemon"
                elif "health_status" in action:
                    ev_type = "health"
                    reason = action
                    msg = f"Health status transition: {action}"

                events_list.append({
                    "timestamp": ts_str,
                    "type": ev_type,
                    "reason": reason,
                    "message": msg,
                })
        except Exception:
            # Fallback if events API times out
            pass

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
            return {"error": f"Docker container lookup failed for {service}: {exc}"}

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

    def what_changed(self, service: str, minutes: int = 60) -> dict[str, Any]:
        """
        Audit recent changes across deploy logs, Docker events, and GitHub API.
        """
        now_ts = time.time()
        cutoff_ts = now_ts - (minutes * 60)
        cutoff_iso = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc).isoformat()
        changes: list[dict[str, Any]] = []

        # 1. Local deploy events from data/deploy_events.jsonl
        if DEPLOY_LOG_PATH.exists():
            try:
                with open(DEPLOY_LOG_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            record_svc = record.get("service")
                            record_ts = record.get("timestamp", "")
                            if (record_svc == service or not service) and record_ts >= cutoff_iso:
                                changes.append({
                                    "timestamp": record_ts,
                                    "type": "deploy",
                                    "source": "deploy_events_log",
                                    "description": record.get("description", f"Deployment for {record_svc}"),
                                    "details": {
                                        "image": record.get("image"),
                                        "trigger": record.get("trigger"),
                                        "scenario_id": record.get("scenario_id"),
                                    },
                                })
                        except Exception:
                            continue
            except Exception:
                pass

        # 2. Docker lifecycle events for container (start, die, restart, update)
        if self.client:
            try:
                container = self._find_container(service)
                if container:
                    filters = {"container": container.id}
                    raw_events = self.client.events(since=int(cutoff_ts), until=int(now_ts), filters=filters, decode=True)
                    for ev in raw_events:
                        action = ev.get("Action", "")
                        time_epoch = ev.get("time", 0)
                        ts_str = datetime.fromtimestamp(time_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                        if action in ["start", "die", "restart", "update", "kill"]:
                            changes.append({
                                "timestamp": ts_str,
                                "type": f"container_{action}",
                                "source": "docker_events",
                                "description": f"Container {service} experienced {action} event",
                                "details": ev.get("Actor", {}).get("Attributes", {}),
                            })
            except Exception:
                pass

        # 3. GitHub REST API (if GITHUB_READ_TOKEN provided)
        gh_token = os.getenv("GITHUB_READ_TOKEN") or os.getenv("GITHUB_TOKEN")
        gh_repo = os.getenv("GITHUB_REPOSITORY", "narang25/chatops-agent")
        if gh_token:
            headers = {
                "Authorization": f"Bearer {gh_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "chatops-what-changed",
            }
            # Commits
            try:
                resp = httpx.get(
                    f"https://api.github.com/repos/{gh_repo}/commits",
                    headers=headers,
                    params={"since": cutoff_iso, "per_page": 5},
                    timeout=3.0,
                )
                if resp.status_code == 200:
                    for c in resp.json():
                        commit_data = c.get("commit", {})
                        author_date = commit_data.get("author", {}).get("date", "")
                        changes.append({
                            "timestamp": author_date,
                            "type": "github_commit",
                            "source": "github_api",
                            "description": f"Commit {c.get('sha', '')[:7]}: {commit_data.get('message', '').splitlines()[0]}",
                            "details": {
                                "sha": c.get("sha"),
                                "author": commit_data.get("author", {}).get("name"),
                            },
                        })
                elif resp.status_code == 403:
                    changes.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "type": "github_rate_limited",
                        "source": "github_api",
                        "description": "GitHub API rate limit exceeded",
                        "details": {"status": 403},
                    })
            except Exception:
                pass

        # Sort all changes by timestamp descending (most recent first)
        changes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return {
            "service": service,
            "window_minutes": minutes,
            "change_count": len(changes),
            "changes": changes,
        }
