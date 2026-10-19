"""Prometheus metrics — matches contracts/metrics.md exactly."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

http_requests_total = Counter("http_requests_total", "Total HTTP requests handled", ["service", "endpoint", "status"])
http_request_duration_seconds = Histogram("http_request_duration_seconds", "HTTP request latency in seconds", ["service", "endpoint"])
app_errors_total = Counter("app_errors_total", "Total application-level errors logged", ["service"])
app_memory_bytes = Gauge("app_memory_bytes", "Current process RSS memory in bytes", ["service"])
app_up = Gauge("app_up", "1 when the service is healthy, 0 otherwise", ["service"])

def get_metrics_response() -> bytes:
    return generate_latest()
