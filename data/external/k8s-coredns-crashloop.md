---
title: "CoreDNS CrashLoopBackOff: DNS Resolution Failure Across Cluster"
failure_type: "crash_loop"
source_type: "external_postmortem"
source_url: "https://k8s.af/coredns-crashloop-forward-loop"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Pods fail to resolve external or internal hostnames. Cluster logs show `dial tcp: lookup kube-dns on 10.96.0.10:53: read: connection refused` or `i/o timeout`. CoreDNS pods are in `CrashLoopBackOff`.

## Likely cause
CoreDNS detected an infinite forwarding loop between upstream nameserver and local CoreDNS resolver (often triggered by loopback 127.0.0.53 in host `/etc/resolv.conf` on systemd-resolved systems).

## How to confirm
Check CoreDNS pod status and logs:
`kubectl get pods -n kube-system -l k8s-app=kube-dns`
`kubectl logs -n kube-system -l k8s-app=kube-dns | grep -i loop`
Look for log message: `Plugin/loop: Loop (127.0.0.1:53 -> :53) detected for zone "."`.

## Fix
1. Edit host `/etc/resolv.conf` or specify upstream DNS in CoreDNS ConfigMap.
2. Edit `kubectl edit cm coredns -n kube-system` and remove loop plugin or point `forward .` to explicit upstream servers (e.g. `8.8.8.8 1.1.1.1`).
3. Restart CoreDNS rollout: `kubectl rollout restart deployment coredns -n kube-system`.
