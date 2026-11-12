---
title: "Node-pressure Eviction"
failure_type: disk_full
source_type: external_doc
source_url: https://kubernetes.io/docs/tasks/administer-cluster/out-of-resource/
license: CC BY 4.0
status: external
---

## Summary
Node-pressure eviction is the process by which the kubelet proactively terminates pods to reclaim resource on nodes.

The kubelet monitors resources like memory, disk space, and filesystem inodes on your cluster's nodes. When one or more of these resources reach specific consumption levels, the kubelet can proactively fail one or more pods on the node to reclaim resources and prevent starvation.

During a node-pressure eviction, the kubelet sets the phase for the selected pods to Failed, and terminates the Pod.

Node-pressure eviction is not the same as API-initiated eviction.

The kubelet does not respect your configured PodDisruptionBudget or the pod's terminationGracePeriodSeconds. If you use soft eviction thresholds, the kubelet respects your configured evictionMaxPodGracePeriod. If you use hard eviction thresholds, the kubelet uses a 0s grace period (immediate shutdown) for termination.

The kubelet attempts to reclaim node-level resources before it terminates end-user pods. For example, it removes unused container images when disk resources are starved.

## Reference
Full article / official documentation: https://kubernetes.io/docs/tasks/administer-cluster/out-of-resource/
