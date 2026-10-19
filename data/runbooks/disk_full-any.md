---
title: "Disk Full: No Space Left on Device"
failure_type: disk_full
service: any
severity: high
---

## Symptoms
- Application writes fail with OS error: `[Errno 28] No space left on device`.
- Structured logs show write errors or filesystem errors:
  `{"timestamp": "2026-10-14T08:22:10.001Z", "service": "payment-service", "level": "ERROR", "message": "Failed to write transaction log: [Errno 28] No space left on device"}`
- Container exits with exit code `1` or the process becomes unresponsive as it cannot flush buffers.
- Docker or system logs contain: `write /var/lib/docker/overlay2/... no space left on device`.
- Prometheus metric `node_filesystem_avail_bytes{mountpoint="/"}` approaches `0`.

## Likely cause
- Excessive log accumulation: application log files or Docker container logs have grown unbounded.
- Large database write-ahead log (WAL) or data volume filling up (Postgres WAL, SQLite WAL).
- Docker overlay2 layers from stale image builds consuming host disk.
- Temporary files created by the application (e.g. uploaded files, export dumps) never deleted.

## How to confirm
1. Check overall disk usage on the host:
   ```bash
   df -h /
   du -sh /var/lib/docker
   ```
2. Find the top disk consumers under Docker:
   ```bash
   docker system df -v
   ```
3. Identify the largest files and directories:
   ```bash
   du -sh /var/log/* | sort -rh | head -20
   du -sh /tmp/* | sort -rh | head -10
   ```
4. Query Prometheus for available filesystem bytes:
   ```promql
   node_filesystem_avail_bytes{mountpoint="/"}
   100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)
   ```

## Fix
1. Immediately free space by pruning unused Docker objects:
   ```bash
   docker system prune -f
   docker volume prune -f
   ```
2. Rotate and truncate container log files if they are the culprit:
   ```bash
   # Truncate a bloated container log (replace <hash> with actual container ID)
   truncate -s 0 /var/lib/docker/containers/<hash>/<hash>-json.log
   ```
3. Remove large temporary or export files:
   ```bash
   find /tmp -name "*.dump" -mtime +1 -delete
   find /var/log -name "*.log" -size +100M -exec truncate -s 50M {} \;
   ```
4. Restart the affected service once space is reclaimed:
   ```bash
   docker compose -f infra/docker-compose.yml restart <service-name>
   ```

## Prevention
- Configure Docker's `log-driver` with `max-size` and `max-file` limits in `/etc/docker/daemon.json`:
  ```json
  {"log-driver": "json-file", "log-opts": {"max-size": "20m", "max-file": "3"}}
  ```
- Add a Prometheus alert when `node_filesystem_avail_bytes{mountpoint="/"} < 2147483648` (2 GB).
- Schedule a weekly cron to run `docker system prune -f` on the host.
- Use external log forwarding (Loki, CloudWatch) instead of local log files for production workloads.
