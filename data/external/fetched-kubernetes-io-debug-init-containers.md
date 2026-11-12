---
title: "Debug Init Containers"
failure_type: bad_config
source_type: external_doc
source_url: https://kubernetes.io/docs/tasks/debug/debug-application/debug-init-containers/
license: CC BY 4.0
status: external
---

## Summary
This page shows how to investigate problems related to the execution of Init Containers. The example command lines below refer to the Pod as <pod-name> and the Init Containers as <init-container-1> and <init-container-2>.

You need to have a Kubernetes cluster, and the kubectl command-line tool must be configured to communicate with your cluster. It is recommended to run this tutorial on a cluster with at least two nodes that are not acting as control plane hosts. If you do not already have a cluster, you can create one by using minikube or you can use one of these Kubernetes playgrounds:

To check the version, enter kubectl version.

You should be familiar with the basics of Init Containers.

You should have Configured an Init Container.

Checking the status of Init Containers

## Reference
Full article / official documentation: https://kubernetes.io/docs/tasks/debug/debug-application/debug-init-containers/
