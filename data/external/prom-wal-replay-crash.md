---
title: "Prometheus Fails to Start: WAL Corrupted on Sudden Shutdown"
failure_type: "crash_loop"
source_type: "external_postmortem"
source_url: "https://k8s.af/prometheus-corrupted-wal-startup-crash"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Prometheus pod is in `CrashLoopBackOff`. Startup logs display: `caller=main.go:812 err="opening storage failed: repair WAL: ... corrupted segment"`.

## Likely cause
Power failure or kernel crash occurred while Prometheus was writing to the write-ahead log (`wal/` directory).

## How to confirm
Examine Prometheus container crash logs:
`kubectl logs -n monitoring deployment/prometheus | grep -i "corrupted segment"`

## Fix
1. Start Prometheus with auto-repair flag:
`--storage.tsdb.wal-compression` and let WAL repair run.
2. If crash loop persists, delete corrupted WAL segment:
Move bad segment: `mv /prometheus/wal/00000042 /tmp/`
3. Restart Prometheus. Only the last 2 hours of un-compacted data are lost; historical compacted blocks remain intact.
