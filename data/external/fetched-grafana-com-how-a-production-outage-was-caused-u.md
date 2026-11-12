---
title: "How a Production Outage Was Caused Using Kubernetes Pod Priorities | Grafana Labs"
failure_type: disk_full
source_type: external_postmortem
source_url: https://grafana.com/blog/2019/07/24/how-a-production-outage-was-caused-using-kubernetes-pod-priorities/
license: Public Postmortem Summary
status: external
---

## Summary
How a Production Outage Was Caused Using Kubernetes Pod Priorities

On Friday, July 19, Grafana Cloud experienced a ~30min outage in our Hosted Prometheus service. To our customers who were affected by the incident, I apologize. It’s our job to provide you with the monitoring tools you need, and when they are not available we make your life harder. We take this outage very seriously. This blog post explains what happened, how we responded to it, and what we’re doing to ensure it doesn’t happen again.

The Grafana Cloud Hosted Prometheus service is based on Cortex, a CNCF project to build a horizontally scalable, highly available, multi-tenant Prometheus service. The Cortex architecture consists of a series of individual microservices, each handling a different role: replication, storage, querying, etc. Cortex is under very active development, continually adding features and increasing performance. We regularly deploy new releases of Cortex to our clusters so that customers see these benefits; Cortex is designed to do so without downtime.

To achieve zero-downtime upgrades, Cortex’s Ingester service requires an extra Ingester replica during the upgrade process. This allows the old Ingesters to send in-progress data to the new Ingesters one by one. But Ingesters are big: They request 4 cores and 15GB of RAM per Pod, 25% of the CPU and memory of a single machine in our Kubernetes clusters. In aggregate, we typically have much more than 4 cores and 15GB RAM of unused resources available on a cluster to run these extra Ingesters for upgrades.

However, it is often the case that

## Reference
Full article / official documentation: https://grafana.com/blog/2019/07/24/how-a-production-outage-was-caused-using-kubernetes-pod-priorities/
