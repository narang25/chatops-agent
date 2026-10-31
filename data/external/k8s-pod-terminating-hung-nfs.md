---
title: "Pod Stuck in Terminating State: Hung Mount or Finalizer"
failure_type: "other"
source_type: "external_doc"
source_url: "https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Pod remains in `Terminating` status indefinitely. `kubectl delete pod` does not complete. New deployments cannot complete rollout.

## Likely cause
A hung NFS/CSI volume unmount blocks container runtime teardown, or an unfulfilled finalizer is present on the pod object.

## How to confirm
Inspect pod finalizers and status:
`kubectl get pod <pod> -o jsonpath='{.metadata.finalizers}'`
Check kubelet error logs:
`journalctl -u kubelet -n 50 | grep -i "unmount"`
Check kernel dmesg for hung filesystem tasks:
`dmesg -T | grep -i "nfs: server not responding"`

## Fix
1. If safe, remove hung finalizer: `kubectl patch pod <pod> -p '{"metadata":{"finalizers":null}}'`.
2. Force delete pod: `kubectl delete pod <pod> --force --grace-period=0`.
3. Unmount hung filesystem on host: `umount -f -l <mount-point>`.
