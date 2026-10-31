---
title: "Corrupted B-Tree Index: Queries Return Partial or Inconsistent Rows"
failure_type: "other"
source_type: "external_postmortem"
source_url: "https://k8s.af/postgres-corrupt-index-after-power-loss"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Query using an index misses existing rows, but `SET enable_indexscan = off;` finds the rows via sequential scan. In severe cases, query crashes with `ERROR: invalid page in block ... of relation ...`.

## Likely cause
Hard power loss or faulty underlying storage controller caused partial block writes in index pages without affecting base heap table.

## How to confirm
Use PostgreSQL `amcheck` extension:
```sql
CREATE EXTENSION amcheck;
SELECT bt_index_check('idx_orders_customer_id', true);
```
Look for corruption errors reported by `amcheck`.

## Fix
1. Rebuild corrupted index concurrently (no lock on reads/writes):
`REINDEX INDEX CONCURRENTLY idx_orders_customer_id;`
2. Verify integrity after rebuild: `SELECT bt_index_check('idx_orders_customer_id', true);`.
3. Check host hardware diagnostics and SMART disk status.
