---
title: "Prometheus Alerting Lag: Rule Evaluation Interval Exceeded"
failure_type: "other"
source_type: "external_doc"
source_url: "https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Alerts fire with significant delay (10-15 minutes after failure starts). Prometheus logs report `Rule group 'alerts' evaluation took 45s, interval is 30s`.

## Likely cause
Complex subqueries or unbounded regex label matching in alert rules (`{__name__=~".*"} [1h]`) take longer to execute than the rule group evaluation interval.

## How to confirm
Query rule evaluation metrics:
`prometheus_rule_group_last_duration_seconds`
`prometheus_rule_group_iterations_missed_total`

## Fix
1. Optimize alert rule queries: avoid subqueries inside alert definitions; use recording rules for precomputing expensive aggregations.
2. Split rules into multiple groups with independent intervals.
3. Increase evaluation interval for non-critical alerts from 15s to 1m.
