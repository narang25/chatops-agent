---
title: "Prometheus Remote Write Queue Full: Dropping Remote Metrics"
failure_type: "other"
source_type: "external_doc"
source_url: "https://prometheus.io/docs/prometheus/latest/configuration/configuration/#remote_write"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Metrics sent to long-term storage (Cortex, Thanos, Grafana Mimir) are delayed or missing. Prometheus metric `prometheus_remote_storage_dropped_samples_total` is increasing.

## Likely cause
Network congestion or rate limiting on the remote storage receiver. Prometheus remote write queue is full and dropping samples.

## How to confirm
Query Prometheus metrics:
`prometheus_remote_storage_queue_highest_sent_timestamp_seconds`
`rate(prometheus_remote_storage_dropped_samples_total[5m]) > 0`
Inspect Prometheus logs for `remote_write: non-recoverable error` or HTTP 429.

## Fix
1. Increase queue capacity in `prometheus.yml`:
```yaml
remote_write:
- url: "https://mimir.internal/api/v1/push"
  queue_config:
    max_shards: 100
    max_samples_per_send: 5000
    capacity: 20000
```
2. Verify network bandwidth and ensure remote receiver is not CPU throttled.
