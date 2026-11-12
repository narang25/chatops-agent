---
title: "StatefulSets"
failure_type: disk_full
source_type: external_doc
source_url: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
license: CC BY 4.0
status: external
---

## Summary
StatefulSet is the workload API object used to manage stateful applications.

Manages the deployment and scaling of a set of Pods, and provides guarantees about the ordering and uniqueness of these Pods.

Like a Deployment, a StatefulSet manages Pods that are based on an identical container spec. Unlike a Deployment, a StatefulSet maintains a sticky identity for each of its Pods. These pods are created from the same spec, but are not interchangeable: each has a persistent identifier that it maintains across any rescheduling.

If you want to use storage volumes to provide persistence for your workload, you can use a StatefulSet as part of the solution. Although individual Pods in a StatefulSet are susceptible to failure, the persistent Pod identifiers make it easier to match existing volumes to the new Pods that replace any that have failed.

StatefulSets are valuable for applications that require one or more of the following:

Ordered, graceful deployment and scaling.

## Reference
Full article / official documentation: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
