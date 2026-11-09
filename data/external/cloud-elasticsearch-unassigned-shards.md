---
title: "Elasticsearch Cluster Red: High Disk Watermark Exceeded"
failure_type: "disk_full"
source_type: "external_doc"
source_url: "https://www.elastic.co/guide/en/elasticsearch/reference/current/disk-watermarks.html"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Elasticsearch cluster health status is `RED`. Search queries fail or return partial results. Logstash or Fluentd buffers fill up because indexing is blocked with `403 Forbidden / cluster_block_exception`.

## Likely cause
Node disk usage exceeded the flood-stage watermark (default 95%). Elasticsearch automatically applied a read-only index block (`read_only_allow_delete`) to prevent disk corruption.

## How to confirm
Check cluster health:
`curl -s localhost:9200/_cluster/health | jq .`
Check allocation explanation:
`curl -s localhost:9200/_cluster/allocation/explain | jq .`
Look for `flood stage disk watermark [95%] exceeded`.

## Fix
1. Delete old indices to free disk space:
`curl -X DELETE "localhost:9200/logs-2026.09.*"`
2. Remove read-only block from all indices:
```bash
curl -X PUT "localhost:9200/_all/_settings" -H 'Content-Type: application/json' -d '{
  "index.blocks.read_only_allow_delete": null
}'
```
3. Configure Curator or Index Lifecycle Management (ILM) to automatically delete or rollover indices older than 30 days.
