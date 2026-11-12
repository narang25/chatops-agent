---
title: "Debug Running Pods"
failure_type: other
source_type: external_doc
source_url: https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/
license: CC BY 4.0
status: external
---

## Summary
This page explains how to debug Pods running (or crashing) on a Node.

Your Pod should already be scheduled and running. If your Pod is not yet running, start with Debugging Pods.

For some of the advanced debugging steps you need to know on which Node the Pod is running and have shell access to run commands on that Node. You don't need that access to run the standard debug steps that use kubectl.

Using kubectl describe pod to fetch details about pods

For this example we'll use a Deployment to create two pods, similar to the earlier example.

Create deployment by running following command:

## Reference
Full article / official documentation: https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/
