---
title: "Debug Services"
failure_type: disk_full
source_type: external_doc
source_url: https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/
license: CC BY 4.0
status: external
---

## Summary
An issue that comes up rather frequently for new installations of Kubernetes is that a Service is not working properly. You've run your Pods through a Deployment (or other workload controller) and created a Service, but you get no response when you try to access it. This document will hopefully help you to figure out what's going wrong.

For many steps here you will want to see what a Pod running in the cluster sees. The simplest way to do this is to run an interactive busybox Pod:

If you already have a running Pod that you prefer to use, you can run a command in it using:

For the purposes of this walk-through, let's run some Pods. Since you're probably debugging your own Service you can substitute your own details, or you can follow along and get a second data point.

kubectl commands will print the type and name of the resource created or mutated, which can then be used in subsequent commands.

Let's scale the deployment to 3 replicas.

## Reference
Full article / official documentation: https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/
