---
title: "Kubernetes Networking Problems Due to the Conntrack // Deploy Live"
failure_type: disk_full
source_type: external_postmortem
source_url: https://deploy.live/blog/kubernetes-networking-problems-due-to-the-conntrack/
license: Public Postmortem Summary
status: external
---

## Summary
Kubernetes Networking Problems Due to the Conntrack

Kubernetes nodes set conntrack_max value proportionally to the size of the RAM on the node. High load applications (especially on small nodes) can easily exceed conntrack_max and result in connection resets and timeouts. There is several options to deal with this issue.

conntrack is a feature built on top of Netlifier framework. It is essential for performant complex networking of Kubernetes where nodes need to track connection information between thousands of pods and services.

Connection tracking allows the kernel to keep track of all logical network connections or sessions, and thereby relate all of the packets which may make up that connection. NAT relies on this information to translate all related packets in the same way, and iptables can use this information to act as a stateful firewall.

conntrack on Linux systems is not unbound, in Kubernetes default value can be found in the node_nf_conntrack_entries_limit prometheus metrics (requires node_exporter) or via:

It is suggested that default conntrack_max is limited to 65k entries and can be calculated with the following formula:

## Reference
Full article / official documentation: https://deploy.live/blog/kubernetes-networking-problems-due-to-the-conntrack/
