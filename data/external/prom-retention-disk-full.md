---
title: "Prometheus Storage Disk Full: TSDB Compaction Failed"
failure_type: "disk_full"
source_type: "external_doc"
source_url: "https://prometheus.io/docs/prometheus/latest/storage/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Prometheus data partition reaches 100% capacity. Logs report `caller=compact.go:501 err="compact head: write block: write /prometheus/...: no space left on device"`.

## Likely cause
Prometheus storage retention configuration `--storage.tsdb.retention.time` was set too long (e.g. 90d) without setting `--storage.tsdb.retention.size`, exceeding disk capacity.

## How to confirm
Check disk space on storage volume:
`df -h /prometheus`
Check current retention settings:
`ps aux | grep prometheus | grep -i retention`

## Fix
1. Configure retention size cap in Prometheus flags:
`--storage.tsdb.retention.size=40GB`
`--storage.tsdb.retention.time=15d`
2. Expand PersistentVolume in Kubernetes:
`kubectl patch pvc prometheus-data -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'`.
