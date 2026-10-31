---
title: "CNI Subnet IP Exhaustion: Pods Stuck in ContainerCreating"
failure_type: "other"
source_type: "external_doc"
source_url: "https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
New pods remain stuck in `ContainerCreating`. Pod events display `failed to allocate for range: no IP addresses available in range set: 10.244.0.0/24`.

## Likely cause
The node or CNI IPAM pool (AWS VPC CNI, Calico, Flannel) has allocated all available IPs. Leaked IP allocations from deleted pods or an overly small podCIDR allocation.

## How to confirm
Inspect pod describe events:
`kubectl describe pod <pod-name> | grep -A 5 Events`
Check Calico IPAM / AWS VPC CNI allocation:
`calicoctl ipam show` or check host IPAM files in `/var/lib/cni/networks/`.

## Fix
1. Release orphaned IP allocations: restart CNI daemonset `kubectl rollout restart ds/calico-node -n kube-system`.
2. Expand node podCIDR subnet mask or assign secondary CIDR blocks in cloud VPC CNI.
3. Drain and replace nodes if local CNI state DB is corrupted.
