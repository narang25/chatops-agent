---
title: "Tools for Monitoring Resources"
failure_type: cpu_saturation
source_type: external_doc
source_url: https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-usage-monitoring/
license: CC BY 4.0
status: external
---

## Summary
To scale an application and provide a reliable service, you need to understand how the application behaves when it is deployed. You can examine application performance in a Kubernetes cluster by examining the containers, pods, services, and the characteristics of the overall cluster. Kubernetes provides detailed information about an application's resource usage at each of these levels. This information allows you to evaluate your application's performance and where bottlenecks can be removed to improve overall performance.

In Kubernetes, application monitoring does not depend on a single monitoring solution. On new clusters, you can use resource metrics or full metrics pipelines to collect monitoring statistics.

The resource metrics pipeline provides a limited set of metrics related to cluster components such as the Horizontal Pod Autoscaler controller, as well as the kubectl top utility. These metrics are collected by the lightweight, short-term, in-memory metrics-server and are exposed via the metrics.k8s.io API.

metrics-server discovers all nodes on the cluster and queries each node's kubelet for CPU and memory usage. The kubelet acts as a bridge between the Kubernetes master and the nodes, managing the pods and containers running on a machine. The kubelet translates each pod into its constituent containers and fetches individual container usage statistics from the container runtime through the container runtime interface. If you use a container runtime that uses Linux cgroups and namespaces to implement containers, and the container runtime does not publish usage sta

## Reference
Full article / official documentation: https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-usage-monitoring/
