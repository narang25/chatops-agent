---
title: "PostgreSQL Cache Hit Ratio Drop: Low shared_buffers"
failure_type: "other"
source_type: "external_doc"
source_url: "https://www.postgresql.org/docs/current/runtime-config-resource.html#GUC-SHARED-BUFFERS"
license: "PostgreSQL License"
status: "summary"
---

## Symptoms
Database latency spikes by 5x. Disk read IOPS reach 100% capacity. Cache hit ratio drops below 95%.

## Likely cause
`shared_buffers` is configured to the default 128MB on a server with 16GB+ RAM, causing almost every query to read directly from disk rather than memory cache.

## How to confirm
Check cache hit ratio:
```sql
SELECT sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_hit_ratio
FROM pg_statio_user_tables;
```
If ratio is below 0.99, memory caching is inadequate.

## Fix
1. Set `shared_buffers = 4GB` (recommended 25% of dedicated server RAM) in `postgresql.conf`.
2. Set `effective_cache_size = 12GB` (75% of total RAM).
3. Restart PostgreSQL service for changes to take effect.
