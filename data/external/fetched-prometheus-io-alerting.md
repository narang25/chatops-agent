---
title: "Alerting"
failure_type: network_timeout
source_type: external_doc
source_url: https://prometheus.io/docs/practices/alerting/
license: Apache-2.0
status: external
---

## Summary
We recommend that you read My Philosophy on Alerting based on Rob Ewaschuk's observations at Google.

To summarize: keep alerting simple, alert on symptoms, have good consoles to allow pinpointing causes, and avoid having pages where there is nothing to do.

There are no strict restrictions regarding the naming of alerting rules, as alert names may contain any number of Unicode characters, just like any other label value. However, the community has rallied around using Camel Case for their alert names.

Aim to have as few alerts as possible, by alerting on symptoms that are associated with end-user pain rather than trying to catch every possible way that pain could be caused. Alerts should link to relevant consoles and make it easy to figure out which component is at fault.

Allow for slack in alerting to accommodate small blips.

Typically alert on high latency and error rates as high up in the stack as possible.

## Reference
Full article / official documentation: https://prometheus.io/docs/practices/alerting/
