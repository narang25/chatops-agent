---
title: "Docker Daemon Unresponsive: containerd Socket Deadlock"
failure_type: "other"
source_type: "external_doc"
source_url: "https://docs.docker.com/engine/troubleshoot-and-support/daemon-troubleshooting/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
`docker ps` hangs indefinitely. New containers cannot be started. Existing containers may still be running but Docker CLI and API do not respond.

## Likely cause
Containerd socket `/run/containerd/containerd.sock` deadlocked due to race condition during high-concurrency container creation/deletion or zombie shim processes.

## How to confirm
Test containerd socket responsiveness:
`crictl --runtime-endpoint unix:///run/containerd/containerd.sock info`
Check if containerd-shim processes are orphaned:
`ps aux | grep containerd-shim | grep defunct`

## Fix
1. Send SIGUSR1 to dockerd to dump goroutine stack traces: `kill -SIGUSR1 $(pidof dockerd)`.
2. Gracefully restart containerd, then docker:
`systemctl restart containerd && systemctl restart docker`
3. If shims remain hung, kill zombie shims: `killall -9 containerd-shim`.
