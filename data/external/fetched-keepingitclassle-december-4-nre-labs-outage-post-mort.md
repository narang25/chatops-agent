---
title: "December 4 - NRE Labs Outage Post-Mortem | Matt Oswalt"
failure_type: disk_full
source_type: external_postmortem
source_url: https://keepingitclassless.net/2018/12/december-4-nre-labs-outage-post-mortem/
license: Public Postmortem Summary
status: external
---

## Summary
December 4 - NRE Labs Outage Post-Mortem

December 5, 2018 in Systems10 minutes

I awoke yesterday to a very crisp Tuesday morning in Portland, Oregon. I had just poured myself a nice glass of Stumptown Nitro cold brew coffee, and wandered upstairs to my office for an 8AM conference call. I joined the meeting, and started going through my usual routine - part of which includes looking at the day’s NRE Labs stats. Here’s what I saw:

First, a few architectural notes on Kubernetes. The Kubernetes “master” is actually three discrete subcomponents:

Underlying these three components is etcd, which is a key/value database that holds all state for Kubernetes. This allow the subcomponents of Kubernetes to remain stateless. However, what this means is that etcd is a crucial component of any Kubernetes cluster. Without etcd, you don’t have Kubernetes. More on that later.

In addition, in the Antidote project specifically, which is what powers NRE Labs, the way we’re currently building our Kubernetes cluster is with a tool called kubeadm. This allows us to easily create a single-master cluster, which is another way of saying that all of the master services, including everything in the above diagram, on a single node - in our case, a virtual machine in GCP.

## Reference
Full article / official documentation: https://keepingitclassless.net/2018/12/december-4-nre-labs-outage-post-mortem/
