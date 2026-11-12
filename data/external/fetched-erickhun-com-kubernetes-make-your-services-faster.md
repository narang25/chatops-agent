---
title: "Kubernetes: Make your services faster by removing CPU limits"
failure_type: network_timeout
source_type: external_postmortem
source_url: https://erickhun.com/posts/kubernetes-faster-services-no-cpu-limits/
license: Public Postmortem Summary
status: external
---

## Summary
Kubernetes: Make your services faster by removing CPU limits

At Buffer, we’ve been using Kubernetes since 2016. We’ve been managing our k8s (kubernetes) cluster with kops, it has about 60 nodes (on AWS), and runs about 1500 containers. Our transition to a micro-service architecture has been full of trial and errors. Even after a few years running k8s, we are still learning its secrets. This post will talk about how something we thought was a good thing, but ended up to be not as great as we thought: CPU limits.

It is s general recommendation to set CPU limits. Google, among others, highly recommends it. The danger of not setting a CPU limit is that containers running in the node could exhaust all CPU available. This can trigger a cascade of unwanted events such as having key Kubernetes processes (such as kubelet) to become unresponsive. So it is in theory a great thing to set CPU limit in order to protect your nodes.

CPU limits is the maximum CPU time a container can uses at a given period (100ms by default). The CPU usage for a container will never go above that limit you specified. Kubernetes use a mechanism called CFS Quota to throttle the container to prevent the CPU usage from going above the limit. That means CPU will be artificially restricted, making the performance of your containers lower (and slower when it comes to latency).

What can happen if we don’t set CPU limits?

We unfortunately experienced the issue. The kubelet , a process running on every node, and in charge of managing the containers (pods) in the nodes became unresponsive. The node will turn into

## Reference
Full article / official documentation: https://erickhun.com/posts/kubernetes-faster-services-no-cpu-limits/
