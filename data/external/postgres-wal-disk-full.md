---
title: "PostgreSQL PANIC: Could Not Write to Log File, Disk Full"
failure_type: "disk_full"
source_type: "external_postmortem"
source_url: "https://k8s.af/postgres-wal-disk-full-panic"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
PostgreSQL server crashes and refuses to start: `PANIC: could not write to log file 000000010000003400000021: No space left on device`. Database is completely down.

## Likely cause
WAL (Write-Ahead Log) archiving command failed (`archive_command` failing), or an inactive replication slot is holding WAL segments, filling the `pg_wal` disk volume.

## How to confirm
Check disk space on data partition: `df -h /var/lib/postgresql/data`.
Check for inactive replication slots holding WAL:
`SELECT slot_name, active, pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS retained_bytes FROM pg_replication_slots;`
Check Postgres logs for `archive_command` errors.

## Fix
1. Drop inactive or abandoned replication slot:
`SELECT pg_drop_replication_slot('abandoned_replica');`
2. If archiving is failing, fix archive script destination or temporarily set `archive_command = '/bin/true'`.
3. Increase storage volume size or set `wal_keep_size` and `max_slot_wal_keep_size` limits in `postgresql.conf`.
