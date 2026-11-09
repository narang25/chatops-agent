---
title: "GitHub Database Partition: Network Blip Causes Split-Brain"
failure_type: "other"
source_type: "external_postmortem"
source_url: "https://github.blog/2018-10-30-oct21-post-incident-analysis/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Site locked in maintenance mode. Database writes disabled. Data inconsistency between primary data center and secondary failover site.

## Likely cause
A 43-second network partition between two data centers caused orchestrator to promote a replica to primary in the secondary site while the original primary continued taking writes, creating split-brain divergence.

## How to confirm
Compare transaction logs (binlog LSN or WAL positions) across database instances.
Check orchestrator failover logs: `orchestrator-client -c which-cluster-instances`.

## Fix
1. Stop writes immediately to prevent further divergence.
2. Designate authoritative primary and extract missing delta transactions from diverged secondary.
3. Use consensus-based quorum (Raft/Paxos) for automated failover so promotion requires a majority vote.
