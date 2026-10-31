---
title: "Prometheus Samples Rejected: Error Out of Order / Duplicate Timestamp"
failure_type: "other"
source_type: "external_doc"
source_url: "https://prometheus.io/docs/prometheus/latest/configuration/configuration/#tsdb"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Prometheus logs report `Error on ingesting samples that are out of order` or `err: duplicate sample for timestamp`. Recent metrics are missing from Grafana.

## Likely cause
Clock drift (NTP desynchronization) between scrape target host and Prometheus server, or multiple target instances pushing identical metrics with backdated timestamps.

## How to confirm
Check host clock synchronization:
`chronyc tracking` or `ntpq -p`
Inspect Prometheus log for out of order errors:
`kubectl logs deployment/prometheus | grep -i "out of order"`

## Fix
1. Resynchronize system clock using NTP: `systemctl restart systemd-timesyncd` or `chronyd`.
2. If ingesting historical data, enable out-of-order ingestion in Prometheus TSDB configuration:
`--storage.tsdb.out-of-order.time-window=10m`
