---
title: "Connection Refused / Dropped: Misconfigured NetworkPolicy"
failure_type: "dependency_failure"
source_type: "external_doc"
source_url: "https://kubernetes.io/docs/concepts/services-networking/network-policies/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Service A cannot reach Service B (`connection timed out` or `no route to host`), but Service B is healthy and pod is running. Direct curl from inside the namespace fails.

## Likely cause
A Kubernetes `NetworkPolicy` selects the namespace or pod with default deny ingress, but lacks an ingress rule matching Service A's namespace or pod label.

## How to confirm
Check active network policies in the namespace:
`kubectl get networkpolicy -n <namespace>`
Inspect ingress/egress rules:
`kubectl describe networkpolicy <policy-name> -n <namespace>`
Test inter-pod connectivity using ephemeral debug container:
`kubectl debug -it <pod> --image=curlimages/curl -- curl -v http://<service-b>:8080/health`

## Fix
1. Add ingress rule allowing traffic from Service A's pod label:
```yaml
ingress:
- from:
  - podSelector:
      matchLabels:
        app: service-a
  ports:
  - protocol: TCP
    port: 8080
```
2. Apply updated NetworkPolicy: `kubectl apply -f networkpolicy.yaml`.
