---
title: "Pod Eviction: The Node Had Condition DiskPressure / Ephemeral Storage"
failure_type: "disk_full"
source_type: "external_doc"
source_url: "https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#local-ephemeral-storage"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Pod status changes to `Evicted`. Describe shows: `Pod ephemeral local storage usage exceeds the total limit of containers 500Mi`. Application is rescheduled on another node.

## Likely cause
Container wrote large files to container root filesystem (`/tmp`, `/var/log`, or unpackaged assets) instead of a mounted volume, exceeding configured ephemeral storage limits.

## How to confirm
Inspect pod eviction message:
`kubectl describe pod <evicted-pod> | grep -i "ephemeral local storage"`
Check directory sizes in the container or on node:
`du -sh /var/lib/kubelet/pods/<pod-uid>/volumes/*`

## Fix
1. Increase `resources.limits.ephemeral-storage` in pod specification.
2. Mount an `emptyDir` or persistent volume for temporary scratch storage.
3. Configure application to stream uploads directly to S3 or clean up temporary files in `finally` blocks.
