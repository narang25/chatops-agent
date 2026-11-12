---
title: "Pod Lifecycle"
failure_type: crash_loop
source_type: external_doc
source_url: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
license: CC BY 4.0
status: external
---

## Summary
This page describes the lifecycle of a Pod. Pods follow a defined lifecycle, starting in the Pending phase, moving through Running if at least one of its primary containers starts OK, and then through either the Succeeded or Failed phases depending on whether any container in the Pod terminated in failure.

While a Pod runs, the kubelet manages containers and translates the Pod's spec for the container runtime. The kubelet also manages executing probes that track the health of your application.

Like individual application containers, Pods are considered to be relatively ephemeral (rather than durable) entities. Pods are created, assigned a unique ID (UID), and scheduled to run on nodes where they remain until termination (according to restart policy) or deletion. If a Node dies, the Pods running on (or scheduled to run on) that node are marked for deletion. The control plane marks the Pods for removal after a timeout period.

While a Pod is running, the kubelet is able to restart containers to handle some kind of faults. Within a Pod, Kubernetes tracks different container states and determines what action to take to make the Pod healthy again. This is done in a polling loop that periodically reconciles the desired state (a Pod spec) with the actual state of the running containers.

In the Kubernetes API, Pods have both a specification and an actual status. The status for a Pod object consists of a set of Pod conditions. You can also inject custom readiness information into the condition data for a Pod, if that is useful to your application.

Pods are only scheduled once in

## Reference
Full article / official documentation: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
