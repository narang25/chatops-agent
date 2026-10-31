---
title: "etcd Database Space Exceeded: Kubernetes API Server Read-Only"
failure_type: "other"
source_type: "external_postmortem"
source_url: "https://k8s.af/etcd-database-space-exceeded"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Kubernetes API server refuses any create/update/delete operations: `etcdserver: mvcc: database space exceeded`. Read queries work, but no state changes can be written.

## Likely cause
etcd database size reached quota limit (default 2GB) due to lack of automatic compaction and defragmentation, compounded by frequent events or high object churn.

## How to confirm
Check etcd endpoint status and alarms:
`etcdctl --cacert=... --cert=... --key=... endpoint status -w table`
`etcdctl alarm list`
Check for alarm: `NOSPACE`.

## Fix
1. Get current etcd revision: `REV=$(etcdctl endpoint status --write-out="json" | jq .[0].Status.header.revision)`.
2. Compact old revisions: `etcdctl compact $REV`.
3. Defragment all etcd member endpoints: `etcdctl defrag --endpoints=https://127.0.0.1:2379`.
4. Disarm the NOSPACE alarm: `etcdctl alarm disarm`.
5. Increase etcd quota in `/etc/kubernetes/manifests/etcd.yaml` to `--quota-backend-bytes=8589934592` (8GB).
