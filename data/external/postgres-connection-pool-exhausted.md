---
title: "PostgreSQL Connection Limit Exceeded: FATAL remaining connection slots"
failure_type: "db_timeout"
source_type: "external_doc"
source_url: "https://www.postgresql.org/docs/current/runtime-config-connection.html"
license: "PostgreSQL License"
status: "summary"
---

## Symptoms
Microservices fail to connect to PostgreSQL: `FATAL: remaining connection slots are reserved for non-replication superuser connections` or `psycopg2.OperationalError: server closed the connection unexpectedly`.

## Likely cause
Connection pool leak in application instances, or sudden scale-out of pods where each pod initializes a pool of 20 connections, surpassing `max_connections` (default 100).

## How to confirm
Query connection count by state and application:
`SELECT state, count(*) FROM pg_stat_activity GROUP BY state;`
`SELECT client_addr, count(*) FROM pg_stat_activity GROUP BY client_addr ORDER BY count(*) DESC;`
Look for large number of connections in `idle` or `idle in transaction` state.

## Fix
1. Terminate idle connections:
`SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < current_timestamp - INTERVAL '15 minutes';`
2. Deploy PgBouncer or Pgpool-II in transaction pooling mode between services and database.
3. Configure application connection pool size: `max_pool_size = 5` per container replica.
