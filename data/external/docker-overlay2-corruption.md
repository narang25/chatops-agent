---
title: "Docker Storage Overlay2 Corruption: Read-Only Filesystem in Container"
failure_type: "other"
source_type: "external_doc"
source_url: "https://docs.docker.com/storage/storagedriver/overlayfs-driver/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Container writes fail with `Read-only file system`. Starting container gives `error creating overlay mount to /var/lib/docker/overlay2/...: structure needs cleaning`.

## Likely cause
Underlying filesystem metadata corruption on `/var/lib/docker/overlay2` following abrupt host power cut or kernel filesystem crash.

## How to confirm
Check kernel dmesg logs:
`dmesg -T | grep -E "(EXT4-fs error|XFS error|overlay2)"`
Check mount status: `mount | grep overlay`.

## Fix
1. Stop Docker daemon: `systemctl stop docker`.
2. Run filesystem check on backing partition: `fsck -y /dev/sdX` (or `xfs_repair`).
3. If corruption is isolated to cached images:
`rm -rf /var/lib/docker/overlay2/*` (warning: deletes local images)
`systemctl start docker` and re-pull images.
