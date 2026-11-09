---
title: "Kafka Consumer Group Rebalance Storm: Message Processing Stall"
failure_type: "high_error_rate"
source_type: "external_postmortem"
source_url: "https://k8s.af/kafka-consumer-rebalance-storm"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Kafka consumer lag increases exponentially. Consumers spend 100% of time in rebalance protocol and 0% processing messages. Consumer logs show `CommitFailedException` and `Revoking previously assigned partitions`.

## Likely cause
A single slow message batch takes longer to process than `max.poll.interval.ms` (default 5 minutes). Kafka broker assumes consumer has died and triggers group rebalance, revoking and reassigning partitions.

## How to confirm
Check consumer lag using Kafka CLI:
`kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group order-processors`
Check consumer logs for `CommitFailedException: Commit cannot be completed since the group has already rebalanced`.

## Fix
1. Reduce `max.poll.records` (e.g. from 500 to 50) to ensure batch completes well within interval.
2. Increase `max.poll.interval.ms` (e.g. to 10 minutes) if individual items have long processing times.
3. Use Cooperative Sticky Assignor (`partition.assignment.strategy = org.apache.kafka.clients.consumer.CooperativeStickyAssignor`) to avoid stop-the-world rebalances.
