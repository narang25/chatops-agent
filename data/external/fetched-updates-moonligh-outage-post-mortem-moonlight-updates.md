---
title: "Outage post-mortem - Moonlight updates"
failure_type: network_timeout
source_type: external_postmortem
source_url: https://updates.moonlightwork.com/outage-post-mortem-87370
license: Public Postmortem Summary
status: external
---

## Summary
Moonlight updates www.moonlightwork.com

From January 18 to January 22, Moonlight's website and API had intermittent outages. These started as occasional API errors but culminated in periods of downtime yesterday. The problems have been resolved, and the application has returned to normal.

Kubernetes is the application hosting software that Moonlight uses. Kubernetes runs applications on groups of servers. The servers are called nodes. Copies of an application that run on the node are called pods. Kubernetes has a scheduler that dynamically decides which pods should run on which nodes.

The original errors on Friday appeared to be connectivity problems with a Redis database. Moonlight's API uses Redis on every authenticated request to validate sessions. We noticed that our Kubernetes monitoring reported that some nodes and pods were unresponsive. Our hosting provider Google Cloud reported networking service disruptions, and we assumed that the outage was the root cause.

As traffic declined over the weekend, the errors seemed to resolve with only occasional problems. On Tuesday morning, the Moonlight website was offline with zero external traffic reaching the cluster. Finding another person on Twitter with similar symptoms led us to believe that Google's hosting was experiencing a networking outage. We contacted Google Cloud Support, who quickly escalated the outage to their support engineering team.

Google's support team identified a pattern in the nodes of our managed Kubernetes cluster. When the nodes experienced periods of sustained 100% CPU usage, the virtual machine

## Reference
Full article / official documentation: https://updates.moonlightwork.com/outage-post-mortem-87370
