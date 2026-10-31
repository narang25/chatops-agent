---
title: "PostgreSQL Streaming Replication Lag: Stale Read Queries"
failure_type: "other"
source_type: "external_doc"
source_url: "https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW"
license: "PostgreSQL License"
status: "summary"
---

## Symptoms
Clients reading from read-replica receive outdated data (e.g. order placed on primary is missing on replica). Replication delay metric grows continuously.

## Likely cause
Network throughput saturation between primary and standby, long-running query on replica causing vacuum conflict, or high write volume exceeding replica apply speed.

## How to confirm
On primary, check replication status:
`SELECT application_name, client_addr, state, sync_state, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes FROM pg_stat_replication;`
On replica, check delay:
`SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;`

## Fix
1. Enable `hot_standby_feedback = on` on replica to inform primary of needed snapshots.
2. Cancel conflicting queries on standby: `max_standby_streaming_delay = 30s`.
3. Check replica disk I/O metrics; optimize I/O provision or scale replica compute.
