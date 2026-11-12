---
title: "Alertmanager"
failure_type: network_timeout
source_type: external_doc
source_url: https://prometheus.io/docs/alerting/latest/alertmanager/
license: Apache-2.0
status: external
---

## Summary
The Alertmanager handles alerts sent by client applications such as the Prometheus server. It takes care of deduplicating, grouping, and routing them to the correct receiver integration such as email, PagerDuty, or OpsGenie. It also takes care of silencing and inhibition of alerts.

The following describes the core concepts the Alertmanager implements. Consult the configuration documentation to learn how to use them in more detail.

Alert generators send alerts to Alertmanager's API. Alertmanager stores active alerts, groups and routes them according to its configuration, applies inhibition and silences, and sends notifications through configured receivers.

In a high-availability deployment, every Alertmanager instance receives alerts independently, while silences and notification state are replicated between peers. See High Availability for details.

Grouping categorizes alerts of similar nature into a single notification. This is especially useful during larger outages when many systems fail at once and hundreds to thousands of alerts may be firing simultaneously.

Example: Dozens or hundreds of instances of a service are running in your cluster when a network partition occurs. Half of your service instances can no longer reach the database. Alerting rules in Prometheus were configured to send an alert for each service instance if it cannot communicate with the database. As a result hundreds of alerts are sent to Alertmanager.

## Reference
Full article / official documentation: https://prometheus.io/docs/alerting/latest/alertmanager/
