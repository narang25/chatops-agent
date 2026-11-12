---
title: "When GKE ran out of IP addresses // Deploy Live"
failure_type: network_timeout
source_type: external_postmortem
source_url: https://deploy.live/blog/when-gke-ran-out-of-ip-addresses/
license: Public Postmortem Summary
status: external
---

## Summary
In our GKE environments, we use Shared VPC functionality to have a separation of concerns between networking and compute projects. This also allows for clearer networking architecture when common networking services need to be shared amongst a number of compute projects, for example, VPN tunnels, Network Peering and Cloud Interconnects. Additionally, GKE offers VPC-native clusters which come with several of scalability and security benefits. This feature allocates pod IPs from a subnet’s secondary range.

One of our clusters runs in a VPC-native mode with a dedicated subnet. The subnet has a /16 subnet mask for IP secondary range, yielding a maximum of 65'536 pods. That’s a lot of pods!

We’ve received a slack message from a colleague saying that deployment of his application takes a long time. On a quick check, we could confirm that an application that normally deploys in minutes has been hanging around for about an hour with only the subset of new pods live. Usually, when deployments are stuck, you expect a missing ConfigMap, Secret or wrong nodeSelector. This time it was something else as about half of the newly deployed pods were running and serving traffic, while the second half was in a pending state.

We saw the following event on the describe of one of the pending pods: Warning FailedScheduling 2m18s (x4 over 3m48s) default-scheduler 0/256 nodes are available: 1 node(s) were unschedulable, 173 Insufficient memory, 214 node(s) didn't match node selector, 87 Insufficient cpu.

Typically, GKE Cluster Autoscaler takes care of node pool scale-ups when there are not enoug

## Reference
Full article / official documentation: https://deploy.live/blog/when-gke-ran-out-of-ip-addresses/
