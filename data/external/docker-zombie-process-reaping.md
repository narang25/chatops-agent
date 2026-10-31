---
title: "PID Limit Exhaustion: Zombie Process Accumulation in Container"
failure_type: "other"
source_type: "external_postmortem"
source_url: "https://k8s.af/docker-zombie-process-pid-exhaustion"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Host or container reports `fork: retry: Resource temporarily unavailable` or `pthread_create failed: Resource temporarily unavailable`. Cannot spawn new processes.

## Likely cause
Application inside container runs as PID 1 without an init system (like `tini`). Child processes exit but their exit status is never reaped by PID 1, accumulating thousands of `<defunct>` zombie processes until host `pids.max` limit is reached.

## How to confirm
Check process list in container:
`docker exec <container> ps aux | grep -i defunct | wc -l`
Check cgroup PID usage:
`cat /sys/fs/cgroup/pids/docker/<id>/pids.current`

## Fix
1. Run container with init process: `docker run --init ...` or add `init: true` in docker-compose.yml.
2. In Dockerfile, use `tini` as entrypoint:
`ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]`
3. Restart container to flush zombies: `docker restart <container>`.
