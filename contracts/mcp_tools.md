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
```

## Person A provides

```
search_runbooks(query: str, top_k: int = 3) -> {
  "query": str,
  "results": [
    {"title": str, "source": str, "failure_type": str, "service": str,
     "score": float, "snippet": str}
  ]
}
```

Errors: tools return `{"error": "<clear message>"}` instead of raising, so the
agent can read the problem and react.
