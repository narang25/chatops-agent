---
title: "Temporary Files Disk Spill: Low work_mem Causes High Latency"
failure_type: "other"
source_type: "external_doc"
source_url: "https://www.postgresql.org/docs/current/runtime-config-resource.html#GUC-WORK-MEM"
license: "PostgreSQL License"
status: "summary"
---

## Symptoms
Queries with `ORDER BY`, `DISTINCT`, or hash joins become extremely slow. High disk write I/O on Postgres data directory. Log message: `temporary file: path ".../pgsql_tmp/...", size 450123456 bytes`.

## Likely cause
`work_mem` setting is too small (default 4MB), forcing PostgreSQL to spill sort and hash operations to temporary disk files instead of RAM.

## How to confirm
Enable temp file logging: `log_temp_files = 0`.
Check Postgres logs for temp file creation:
`grep "temporary file" /var/log/postgresql/*.log`
Check query plan: `EXPLAIN ANALYZE SELECT ...` look for `Sort Method: external merge Disk: 45000kB`.

## Fix
1. Increase `work_mem` globally in `postgresql.conf` (e.g. `work_mem = 64MB`).
2. Or set it per-session for heavy reporting queries: `SET work_mem = '256MB';`.
3. Ensure server RAM is sufficient: `work_mem * max_connections` should not exceed total RAM.
