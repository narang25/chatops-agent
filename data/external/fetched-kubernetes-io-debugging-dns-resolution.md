---
title: "Debugging DNS Resolution"
failure_type: network_timeout
source_type: external_doc
source_url: https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/
license: CC BY 4.0
status: external
---

## Summary
This page provides hints on diagnosing DNS problems.

You need to have a Kubernetes cluster, and the kubectl command-line tool must be configured to communicate with your cluster. It is recommended to run this tutorial on a cluster with at least two nodes that are not acting as control plane hosts. If you do not already have a cluster, you can create one by using minikube or you can use one of these Kubernetes playgrounds:

Your Kubernetes server must be at or later than version v1.6.

To check the version, enter kubectl version.

Create a simple Pod to use as a test environment

Once that Pod is running, you can exec nslookup in that environment. If you see something like the following, DNS is working correctly.

## Reference
Full article / official documentation: https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/
