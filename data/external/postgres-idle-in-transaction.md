---
title: "Idle In Transaction Connections: Table Bloat and Vacuum Blocked"
failure_type: "db_timeout"
source_type: "external_postmortem"
source_url: "https://k8s.af/postgres-idle-in-transaction-bloat"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Table disk usage swells 10x (table bloat). Query latency increases steadily. Autovacuum runs constantly but reports dead tuples cannot be removed.

## Likely cause
Client opened a transaction (`BEGIN`), executed a query, but never called `COMMIT` or `ROLLBACK` due to unhandled application exception or network timeout.

## How to confirm
Find all idle in transaction queries open longer than 5 minutes:
```sql
SELECT pid, usename, client_addr, state, state_change, query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND state_change < current_timestamp - INTERVAL '5 minutes';
```

## Fix
1. Terminate offending backends:
`SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < current_timestamp - INTERVAL '5 minutes';`
2. Set safety timeout in `postgresql.conf`:
`idle_in_transaction_session_timeout = 60000` (terminates sessions idle in transaction after 60s).
3. Fix application code to use context managers (`with db.session:`) ensuring rollback on error.
