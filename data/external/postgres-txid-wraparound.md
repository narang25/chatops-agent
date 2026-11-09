---
title: "PostgreSQL Emergency Shutdown: Transaction ID Wraparound Freeze"
failure_type: "db_timeout"
source_type: "external_doc"
source_url: "https://www.postgresql.org/docs/current/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND"
license: "PostgreSQL License"
status: "summary"
---

## Symptoms
PostgreSQL stops accepting all write connections: `FATAL: database is not accepting commands to avoid wraparound data loss in database "orders"`. Application queries fail immediately.

## Likely cause
PostgreSQL 32-bit transaction counter reached 2 billion transactions without aggressive autovacuum freeze running to advance `relfrozenxid`.

## How to confirm
Check transaction age for all databases:
`SELECT datname, age(datfrozenxid) FROM pg_database ORDER BY 2 DESC;`
Check Postgres log file for warning:
`WARNING: database "orders" must be vacuumed within 10000000 transactions`.

## Fix
1. Restart PostgreSQL in single-user maintenance mode:
`postgres --single -D /var/lib/postgresql/data orders`
2. Run full freeze vacuum:
`VACUUM FREEZE ANALYZE;`
3. Tune autovacuum to prevent recurrence:
`autovacuum_freeze_max_age = 200000000`
`autovacuum_vacuum_cost_limit = 2000`
