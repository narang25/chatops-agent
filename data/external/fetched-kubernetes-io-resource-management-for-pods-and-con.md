---
title: "Resource Management for Pods and Containers"
failure_type: cpu_saturation
source_type: external_doc
source_url: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
license: CC BY 4.0
status: external
---

## Summary
Resource Management for Pods and Containers

Resource Management for Pods and Containers

When you specify a Pod, you can optionally specify how much of each resource a container needs. The most common resources to specify are CPU and memory (RAM); there are others.

When you specify the resource request for containers in a Pod, the kube-scheduler uses this information to decide which node to place the Pod on. When you specify a resource limit for a container, the kubelet enforces those limits so that the running container is not allowed to use more of that resource than the limit you set. The kubelet also reserves at least the request amount of that system resource specifically for that container to use.

If the node where a Pod is running has enough of a resource available, it's possible (and allowed) for a container to use more resource than its request for that resource specifies.

For example, if you set a memory request of 256 MiB for a container, and that container is in a Pod scheduled to a Node with 8GiB of memory and no other Pods, then the container can try to use more RAM.

## Reference
Full article / official documentation: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
