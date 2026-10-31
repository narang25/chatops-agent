---
title: "RabbitMQ Alarm Triggered: Publishers Blocked by Memory Threshold"
failure_type: "other"
source_type: "external_doc"
source_url: "https://www.rabbitmq.com/docs/alarms"
license: "Mozilla Public License 2.0"
status: "summary"
---

## Symptoms
Microservices publishing messages to RabbitMQ hang on `basic_publish` or receive `RESOURCE_LOCKED` error. Queue processing stalls.

## Likely cause
RabbitMQ memory usage exceeded high watermark threshold (default 40% of installed RAM), triggering a global publishing alarm that blocks all socket connections from writing.

## How to confirm
Check RabbitMQ node status:
`rabbitmqctl status | grep -A 5 alarms`
Check memory usage:
`rabbitmq-diagnostics memory_breakdown`
Look for alarm: `resource_alarm: memory`.

## Fix
1. Temporarily increase memory watermark limit:
`rabbitmqctl set_vm_memory_high_watermark 0.6`
2. Configure lazy queues (`x-queue-mode: lazy`) which page messages to disk immediately instead of keeping them in RAM.
3. Scale consumer instances to drain deep queues and release memory.
