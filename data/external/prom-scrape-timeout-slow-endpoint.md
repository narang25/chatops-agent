---
title: "Prometheus Scrape Target Timeout: context deadline exceeded"
failure_type: "network_timeout"
source_type: "external_doc"
source_url: "https://prometheus.io/docs/prometheus/latest/querying/basics/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Prometheus targets page (`/targets`) shows endpoint in `DOWN` state with error `context deadline exceeded`. Metric `up{job="order-service"} == 0`.

## Likely cause
The application `/metrics` endpoint takes longer than `scrape_timeout` (default 10s) to generate text payload, often due to computing complex runtime stats or holding locks.

## How to confirm
Test `/metrics` response time directly from command line:
`time curl -s -o /dev/null http://order-service:8003/metrics`
If duration exceeds 10s, scrape timeout will trigger.

## Fix
1. Optimize `/metrics` endpoint to serve cached metrics rather than computing live aggregations.
2. In `prometheus.yml`, temporarily increase scrape timeout for that job:
```yaml
scrape_interval: 30s
scrape_timeout: 25s
```
3. Reload Prometheus: `curl -X POST http://localhost:9090/-/reload`.
