---
title: "Prometheus Memory OOM Crash: Metric High-Cardinality Explosion"
failure_type: "out_of_memory"
source_type: "external_postmortem"
source_url: "https://k8s.af/prometheus-high-cardinality-oom"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Prometheus container crashes with exit code 137 (`OOMKilled: true`). Memory usage climbs vertically right before crash. Dashboards and alerting go dark.

## Likely cause
A newly deployed service added high-cardinality labels (e.g. `user_id`, `order_id`, `email`, or `ip_address`) to a Prometheus counter or histogram, creating millions of unique time series.

## How to confirm
Query Prometheus TSDB status API:
`curl -s http://localhost:9090/api/v1/status/tsdb | jq .`
Look at `seriesCountByMetricName` for metrics with > 100,000 series.
Inspect recent commits for `prometheus.NewCounterVec` label definitions.

## Fix
1. Drop offending high-cardinality metrics in Prometheus `metric_relabel_configs`:
```yaml
metric_relabel_configs:
- source_labels: [__name__]
  regex: 'http_requests_per_user_total'
  action: drop
```
2. Remove high-cardinality labels from application code and redeploy service.
3. Reload Prometheus configuration: `curl -X POST http://localhost:9090/-/reload`.
