# Prometheus metrics exposed at /metrics by each sample service

| Metric | Type | Meaning |
|---|---|---|
| http_requests_total{service, endpoint, status} | counter | requests handled |
| http_request_duration_seconds{service, endpoint} | histogram | request latency |
| app_errors_total{service} | counter | application errors logged |
| app_memory_bytes{service} | gauge | process memory (RSS) |
| app_up{service} | gauge | 1 when healthy |

Container metrics (CPU, memory usage and limit) come from cAdvisor.
