---
title: "Pod Priority and Preemption"
failure_type: network_timeout
source_type: external_doc
source_url: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/
license: CC BY 4.0
status: external
---

## Summary
Pods can have priority. Priority indicates the importance of a Pod relative to other Pods. If a Pod cannot be scheduled, the scheduler tries to preempt (evict) lower priority Pods to make scheduling of the pending Pod possible.

In a cluster where not all users are trusted, a malicious user could create Pods at the highest possible priorities, causing other Pods to be evicted/not get scheduled. An administrator can use ResourceQuota to prevent users from creating pods at high priorities.

See limit Priority Class consumption by default for details.

Create Pods withpriorityClassName set to one of the added PriorityClasses. Of course you do not need to create the Pods directly; normally you would add priorityClassName to the Pod template of a collection object like a Deployment.

Keep reading for more information about these steps.

A PriorityClass is a non-namespaced object that defines a mapping from a priority class name to the integer value of the priority. The name is specified in the name field of the PriorityClass object's metadata. The value is specified in the required value field. The higher the value, the higher the priority. The name of a PriorityClass object must be a valid DNS subdomain name, and it cannot be prefixed with system-.

## Reference
Full article / official documentation: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/
