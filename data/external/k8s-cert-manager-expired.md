---
title: "mTLS / Ingress TLS Certificate Expiration in Service Mesh"
failure_type: "other"
source_type: "external_postmortem"
source_url: "https://k8s.af/service-mesh-mtls-cert-expiration"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Inter-service communication fails with TLS handshake errors (`remote error: tls: bad certificate` or `certificate has expired`). Ingress routes fail with browser HTTPS warnings.

## Likely cause
cert-manager or Istio Citadel failed to auto-renew internal root CA or leaf certificates before expiration, causing proxy mTLS validation failures.

## How to confirm
Check cert-manager certificate status:
`kubectl get certificates -A`
Inspect certificate expiry:
`kubectl describe certificate <cert-name> -n <namespace>`
Check Envoy proxy logs:
`kubectl logs <pod-name> -c istio-proxy | grep -i "tls handshake"`

## Fix
1. Trigger manual certificate reissue: `kubectl cert-manager renew <cert-name> -n <namespace>`.
2. Verify cert-manager webhook and controller are running: `kubectl get pods -n cert-manager`.
3. If using Istio mesh CA, restart istiod and rolling restart affected pods to rotate leaf certificates.
