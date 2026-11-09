---
title: "Ingress NGINX 502 Bad Gateway: Upstream Connection Dropped"
failure_type: "high_error_rate"
source_type: "external_doc"
source_url: "https://kubernetes.github.io/ingress-nginx/user-guide/troubleshooting/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
External clients receive HTTP 502 Bad Gateway when routing requests through ingress-nginx to backend services. Ingress controller logs report `upstream prematurely closed connection while reading response header`.

## Likely cause
Keepalive timeout mismatch between NGINX ingress and backend service (backend closes idle connection before NGINX), or backend service crashed while processing request.

## How to confirm
Inspect ingress access logs:
`kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep " 502 "`
Check backend service pod restart counts:
`kubectl get pods -l app=<backend-service>`
Verify keepalive configuration on backend and ingress annotations.

## Fix
1. Ensure backend service `keepalive_timeout` is higher than Ingress proxy timeout (e.g. backend = 65s, ingress = 60s).
2. Add ingress annotation: `nginx.ingress.kubernetes.io/proxy-read-timeout: "60"`.
3. Check backend memory/OOM kills: `kubectl describe pod <backend-pod>`.
