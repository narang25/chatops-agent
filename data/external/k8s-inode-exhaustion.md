---
title: "Node Disk Inode Exhaustion: Pods Evicted with DiskPressure"
failure_type: "disk_full"
source_type: "external_doc"
source_url: "https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Nodes report `DiskPressure` taint even though `df -h` shows ample gigabytes free. Pods fail with `NodeHasDiskPressure` or `no space left on device` during file write.

## Likely cause
File system inode exhaustion (`df -i` shows 100% inode usage). Thousands of tiny temporary files, PHP session files, or un-rotated container log files have consumed all available inode slots.

## How to confirm
Check inode usage on the node:
`df -ih`
Find directory with excessive file count:
`find /var/lib/docker/overlay2 -maxdepth 3 -type d -exec echo -n "{} " \; -exec ls -1 {} \; | wc -l`
Check kubelet events for DiskPressure:
`kubectl describe node <node-name> | grep -i diskpressure`

## Fix
1. Prune unused docker images and stopped containers: `docker system prune -a --volumes` or `crictl rmi --prune`.
2. Locate and delete directory with millions of tiny files: `find /tmp -type f -mtime +7 -delete`.
3. Configure logrotate on host and enforce container ephemeral storage limits in pod specs.
