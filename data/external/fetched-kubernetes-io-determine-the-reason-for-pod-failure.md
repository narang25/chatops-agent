---
title: "Determine the Reason for Pod Failure"
failure_type: bad_config
source_type: external_doc
source_url: https://kubernetes.io/docs/tasks/debug/debug-application/determine-reason-pod-failure/
license: CC BY 4.0
status: external
---

## Summary
Determine the Reason for Pod Failure

Determine the Reason for Pod Failure

This page shows how to write and read a Container termination message.

Termination messages provide a way for containers to write information about fatal events to a location where it can be easily retrieved and surfaced by tools like dashboards and monitoring software. In most cases, information that you put in a termination message should also be written to the general Kubernetes logs.

You need to have a Kubernetes cluster, and the kubectl command-line tool must be configured to communicate with your cluster. It is recommended to run this tutorial on a cluster with at least two nodes that are not acting as control plane hosts. If you do not already have a cluster, you can create one by using minikube or you can use one of these Kubernetes playgrounds:

Writing and reading a termination message

## Reference
Full article / official documentation: https://kubernetes.io/docs/tasks/debug/debug-application/determine-reason-pod-failure/
