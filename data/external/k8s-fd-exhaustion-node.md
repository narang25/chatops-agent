---
title: "Node Out of File Descriptors: Too Many Open Files in System"
failure_type: "other"
source_type: "external_doc"
source_url: "https://kubernetes.io/docs/tasks/administer-cluster/sysctl-cluster/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Applications on a node fail with `socket: too many open files in system` or `open /dev/null: too many open files`. System-wide file descriptor limit reached.

## Likely cause
Host kernel parameter `fs.file-max` is set too low for the aggregate number of pods, or a rogue pod leaked socket connections.

## How to confirm
Check current system-wide FD allocation:
`cat /proc/sys/fs/file-nr`
(Column 1: allocated FDs, Column 2: allocated unused, Column 3: max limit).
Identify processes with highest open file count:
`lsof -n | awk '{print $2}' | sort | uniq -c | sort -nr | head -10`

## Fix
1. Temporarily increase host limit: `sysctl -w fs.file-max=2097152`.
2. Persist in `/etc/sysctl.d/99-kubernetes.conf`: `fs.file-max = 2097152`.
3. Set container securityContext ulimit in pod spec:
```yaml
securityContext:
  sysctls:
  - name: fs.file-max
    value: "2097152"
```
