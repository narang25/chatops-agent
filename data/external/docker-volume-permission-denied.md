---
title: "Permission Denied on Host Volume Mount: Non-Root UID Mismatch"
failure_type: "bad_config"
source_type: "external_doc"
source_url: "https://docs.docker.com/storage/volumes/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Application container crashes on startup with `EACCES: permission denied, open '/data/app.log'` or `mkdir: cannot create directory '/var/data': Permission denied`.

## Likely cause
Container runs as non-root user (e.g. UID 1000 or `node`), but host directory mounted via bind mount is owned by `root:root` (UID 0) with mode 755.

## How to confirm
Inspect container user ID:
`docker inspect <container> --format '{{.Config.User}}'`
Check host directory ownership:
`ls -ld /path/to/host/mount`

## Fix
1. Change ownership of host directory to match container UID:
`chown -R 1000:1000 /path/to/host/mount`
2. Or run container with matching UID in docker-compose.yml: `user: "${UID}:${GID}"`.
3. Use named Docker volumes instead of host bind mounts when file permissions should be managed by Docker.
