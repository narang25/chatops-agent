---
title: "DNS for Services and Pods"
failure_type: network_timeout
source_type: external_doc
source_url: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/
license: CC BY 4.0
status: external
---

## Summary
Kubernetes creates DNS records for Services and Pods. You can contact Services with consistent DNS names instead of IP addresses.

Kubernetes publishes information about Pods and Services which is used to program DNS. kubelet configures Pods' DNS so that running containers can look up Services by name rather than IP.

Services defined in the cluster are assigned DNS names. By default, a client Pod's DNS search list includes the Pod's own namespace and the cluster's default domain.

A DNS query may return different results based on the namespace of the Pod making it. DNS queries that don't specify a namespace are limited to the Pod's namespace. Access Services in other namespaces by specifying it in the DNS query.

For example, consider a Pod in a test namespace. A data Service is in the prod namespace.

A query for data returns no results, because it uses the Pod's test namespace.

## Reference
Full article / official documentation: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/
