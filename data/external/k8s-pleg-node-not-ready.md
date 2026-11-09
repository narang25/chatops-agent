---
title: "Kubelet PLEG Timeout: Node Changes State to NotReady"
failure_type: "other"
source_type: "external_doc"
source_url: "https://kubernetes.io/docs/tasks/debug/debug-cluster/monitor-node-health/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Kubernetes nodes intermittently switch to `NotReady`. Pods on the node are evicted or fail readiness probes. Kubelet logs contain `PLEG is not healthy`.

## Likely cause
Process Lifecycle Event Generator (PLEG) is blocked waiting for container runtime (containerd/dockerd) inspect or list calls, often due to high container churn, zombie containers, or slow filesystem I/O.

## How to confirm
Check node conditions:
`kubectl describe node <node-name> | grep -A 5 Conditions`
Check kubelet journal logs:
`journalctl -u kubelet -n 100 --no-pager | grep -i pleg`
Check containerd responsiveness:
`crictl ps` or `crictl pods` to see if CLI hangs.

## Fix
1. Inspect containerd socket responsiveness: `systemctl status containerd`.
2. Clean up dead/orphaned containers: `crictl rm $(crictl ps -a -q --state Exited)`.
3. If node is disk-bound, check I/O wait with `iostat -xz 1 5` and relieve disk contention.
4. Restart containerd and kubelet: `systemctl restart containerd && systemctl restart kubelet`.
