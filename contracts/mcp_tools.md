# MCP tools

Do not rename tools or change shapes without a contract PR approved by both people.

## Person B provides

```
get_metrics(service: str, metric: str, minutes: int = 5) -> {
  "service": str, "metric": str, "window_minutes": int,
  "latest": float|null, "min": float|null, "max": float|null,
  "samples": [[unix_ts, value], ...]
}

get_pod_status(service: str) -> {
  "service": str,
  "state": "running|restarting|exited|oom_killed|unhealthy|not_found",
  "restart_count": int, "exit_code": int|null, "oom_killed": bool,
  "health": "healthy|unhealthy|none",
  "started_at": str|null, "memory_limit_mb": int|null
}

get_events(service: str, minutes: int = 15) -> {
  "service": str,
  "events": [{"timestamp": str, "type": str, "reason": str, "message": str}]
}

get_logs(service: str, minutes: int = 10, level: str|null = null, limit: int = 100) -> {
  "service": str,
  "count": int,
  "lines": [{"timestamp": str, "level": str, "message": str}]
}

list_services() -> {
  "services": [{"name": str, "state": str}]
}

get_anomalies(service: str, minutes: int = 10) -> {
  "service": str,
  "window_minutes": int,
  "metric_changes": [{"metric": str, "baseline": float, "current": float, "change_pct": float}],
  "new_log_patterns": [{"pattern": str, "count": int, "level": str, "first_seen": str}]
}

what_changed(service: str, hours: int = 24) -> {
  "service": str,
  "changes": [{"timestamp": str, "type": "commit|workflow_run|deploy", "summary": str, "author": str}]
}

propose_remediation(service: str, action: str, params: dict) -> {
  "proposal_id": str,
  "action": str,
  "params": dict,
  "dry_run": {"changes": [str], "risk": "low|medium|high"},
  "requires_approval": true
}
```

## Person A provides

```
search_runbooks(query: str, top_k: int = 3, include_external: bool = true) -> {
  "query": str,
  "results": [
    {"title": str, "source": str, "failure_type": str, "service": str,
     "score": float, "snippet": str,
     "source_type": "internal_runbook|external_postmortem|external_doc|past_incident",
     "url": str|null}
  ],
  "no_confident_match": bool
}
```

## Safety Rule
The agent has **no tool that applies a change**. Applying a remediation happens only through Person B's approval flow (e.g. a Slack button with an approval token), never directly through the agent.

Errors: tools return `{"error": "<clear message>"}` instead of raising, so the
agent can read the problem and react.
