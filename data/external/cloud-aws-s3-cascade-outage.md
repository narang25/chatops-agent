---
title: "AWS S3 Cascading Outage: Command Typo Removes Core Capacity"
failure_type: "dependency_failure"
source_type: "external_postmortem"
source_url: "https://aws.amazon.com/message/41926/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
All operations against S3 in us-east-1 fail. Downstream AWS services (EC2 build systems, Lambda, SQS) fail because they depend on S3 metadata storage.

## Likely cause
An operator debugging an issue executed a command with an incorrect parameter, taking down a far larger number of S3 subsystem servers than intended, requiring a full cold start of S3 subsystems that had never been cold-restarted at scale.

## How to confirm
Inspect service health dashboard for dependency failures:
Check if internal API calls to object storage return 500/503.
Check cascading timeouts in services relying on centralized configuration buckets.

## Fix
1. Implement strict command validation and rate-limiting on destructive administrative tools.
2. Decouple critical service bootpaths from external dependencies: services should cache required configuration locally.
3. Partition failure domains into smaller independent cells to avoid single blast radius.
