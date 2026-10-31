---
title: "PostgreSQL Deadlock Detected: Concurrent Row Lock Contention"
failure_type: "db_timeout"
source_type: "external_doc"
source_url: "https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-DEADLOCKS"
license: "PostgreSQL License"
status: "summary"
---

## Symptoms
Transactions aborted with `ERROR: deadlock detected` / `DETAIL: Process 14023 waits for ShareLock on transaction 88921; Process 14028 waits for ExclusiveLock`. API endpoints return 500.

## Likely cause
Two concurrent transactions updated the same set of rows in different order, creating a mutual dependency cycle.

## How to confirm
Check active locks in PostgreSQL:
```sql
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

## Fix
1. Ensure all code paths acquire row locks in the same consistent order (e.g. `ORDER BY id`).
2. Add `SELECT ... FOR UPDATE SKIP LOCKED` or `NOWAIT` for queue processing patterns.
3. Tune `deadlock_timeout` (default 1s) and ensure application implements exponential backoff retry.
