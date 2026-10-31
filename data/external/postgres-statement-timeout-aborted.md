---
title: "statement_timeout Abort: Long Queries Terminated by Database"
failure_type: "db_timeout"
source_type: "external_doc"
source_url: "https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-STATEMENT-TIMEOUT"
license: "PostgreSQL License"
status: "summary"
---

## Symptoms
Application throws `ERROR: canceling statement due to statement timeout`. Background reports or end-of-day reconciliation jobs fail midway.

## Likely cause
The query duration exceeded `statement_timeout` configured in `postgresql.conf` or user role level.

## How to confirm
Check current timeout setting:
`SHOW statement_timeout;`
Inspect failed query in Postgres logs: `grep "canceling statement due to statement timeout" postgresql.log`.

## Fix
1. Optimize the slow query by adding missing index or refining WHERE clause.
2. For specific background workers, override timeout on connection: `SET statement_timeout = '300s';`.
3. If table is missing index, create index concurrently: `CREATE INDEX CONCURRENTLY idx_orders_created ON orders (created_at);`.
