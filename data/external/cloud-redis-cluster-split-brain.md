---
title: "Redis Sentinel / Cluster Split-Brain: Data Loss During Partition"
failure_type: "other"
source_type: "external_postmortem"
source_url: "https://k8s.af/redis-sentinel-split-brain-data-loss"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Clients write data successfully to Redis, but reads after network recovery show missing keys (data loss). Two nodes claim to be master simultaneously.

## Likely cause
Network partition isolated the old master with a subset of clients while Sentinel elected a new master on the other side. When partition healed, the old master was demoted to replica and its new writes were overwritten by the new master's dataset.

## How to confirm
Check role of all Redis nodes:
`redis-cli -h node1 info replication`
`redis-cli -h node2 info replication`
Check if multiple nodes report `role:master`.

## Fix
1. Configure `min-replicas-to-write 1` and `min-replicas-max-lag 10` in `redis.conf` (master refuses writes if it cannot communicate with at least 1 healthy replica).
2. Ensure Sentinel quorum `sentinel monitor mymaster <ip> <port> <quorum>` is set to majority of Sentinel nodes.
