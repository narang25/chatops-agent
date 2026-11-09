---
title: "PostgreSQL Slow Query Plan: Stale Statistics After Bulk Insert"
failure_type: "other"
source_type: "external_doc"
source_url: "https://www.postgresql.org/docs/current/routine-vacuuming.html#VACUUM-FOR-STATISTICS"
license: "PostgreSQL License"
status: "summary"
---

## Symptoms
Previously fast queries suddenly take 10+ seconds. PostgreSQL query planner selects full sequential table scan instead of using available B-Tree index.

## Likely cause
Bulk INSERT or UPDATE modified table row count significantly without updating the query planner statistics table `pg_statistic`.

## How to confirm
Run EXPLAIN ANALYZE on slow query:
`EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42;`
Compare `expected rows` vs `actual rows` in the explain plan (order of magnitude difference indicates stale statistics).

## Fix
1. Run manual analyze on affected table:
`ANALYZE orders;` or `VACUUM ANALYZE orders;`
2. Tune autovacuum analyze threshold in `postgresql.conf`:
`autovacuum_analyze_scale_factor = 0.05`
`autovacuum_analyze_threshold = 50`
