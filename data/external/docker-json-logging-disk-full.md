---
title: "Unbounded json-file Logging Driver Fills Host Root Disk"
failure_type: "disk_full"
source_type: "external_doc"
source_url: "https://docs.docker.com/config/containers/logging/json-file/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Host disk usage reaches 100%. `df -h` shows `/var/lib/docker` taking all space. Containers cannot write logs and crash.

## Likely cause
Default Docker `json-file` logging driver has no log rotation configured by default. Container logs write continuously to `*-json.log` until disk fills completely.

## How to confirm
Locate massive log files:
`find /var/lib/docker/containers/ -name "*-json.log" -size +1G`
Check current logging driver: `docker info | grep "Logging Driver"`.

## Fix
1. Truncate current bloated log file without restarting container:
`truncate -s 0 /var/lib/docker/containers/<id>/<id>-json.log`
2. Configure default log rotation in `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
```
3. Restart docker service: `systemctl restart docker`.
