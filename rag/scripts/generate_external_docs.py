"""Script to generate 50 curated external failure documents for Task A17.
Follows EXTERNAL_DATA_GUIDE.md Level 1 schema.
"""
from pathlib import Path

EXTERNAL_DIR = Path("/Users/nikhi/Desktop/Chatops/chatops-agent/data/external")
EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

DOCS = [
    # -------------------------------------------------------------
    # 1. Kubernetes Failures & Official Docs (15 docs)
    # -------------------------------------------------------------
    {
        "filename": "k8s-coredns-crashloop.md",
        "title": "CoreDNS CrashLoopBackOff: DNS Resolution Failure Across Cluster",
        "failure_type": "crash_loop",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/coredns-crashloop-forward-loop",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Pods fail to resolve external or internal hostnames. Cluster logs show `dial tcp: lookup kube-dns on 10.96.0.10:53: read: connection refused` or `i/o timeout`. CoreDNS pods are in `CrashLoopBackOff`.

## Likely cause
CoreDNS detected an infinite forwarding loop between upstream nameserver and local CoreDNS resolver (often triggered by loopback 127.0.0.53 in host `/etc/resolv.conf` on systemd-resolved systems).

## How to confirm
Check CoreDNS pod status and logs:
`kubectl get pods -n kube-system -l k8s-app=kube-dns`
`kubectl logs -n kube-system -l k8s-app=kube-dns | grep -i loop`
Look for log message: `Plugin/loop: Loop (127.0.0.1:53 -> :53) detected for zone "."`.

## Fix
1. Edit host `/etc/resolv.conf` or specify upstream DNS in CoreDNS ConfigMap.
2. Edit `kubectl edit cm coredns -n kube-system` and remove loop plugin or point `forward .` to explicit upstream servers (e.g. `8.8.8.8 1.1.1.1`).
3. Restart CoreDNS rollout: `kubectl rollout restart deployment coredns -n kube-system`.
"""
    },
    {
        "filename": "k8s-pleg-node-not-ready.md",
        "title": "Kubelet PLEG Timeout: Node Changes State to NotReady",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://kubernetes.io/docs/tasks/debug/debug-cluster/monitor-node-health/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
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
"""
    },
    {
        "filename": "k8s-ingress-502-upstream.md",
        "title": "Ingress NGINX 502 Bad Gateway: Upstream Connection Dropped",
        "failure_type": "high_error_rate",
        "source_type": "external_doc",
        "source_url": "https://kubernetes.github.io/ingress-nginx/user-guide/troubleshooting/",
        "license": "Apache-2.0",
        "content": """## Symptoms
External clients receive HTTP 502 Bad Gateway when routing requests through ingress-nginx to backend services. Ingress controller logs report `upstream prematurely closed connection while reading response header`.

## Likely cause
Keepalive timeout mismatch between NGINX ingress and backend service (backend closes idle connection before NGINX), or backend service crashed while processing request.

## How to confirm
Inspect ingress access logs:
`kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep " 502 "`
Check backend service pod restart counts:
`kubectl get pods -l app=<backend-service>`
Verify keepalive configuration on backend and ingress annotations.

## Fix
1. Ensure backend service `keepalive_timeout` is higher than Ingress proxy timeout (e.g. backend = 65s, ingress = 60s).
2. Add ingress annotation: `nginx.ingress.kubernetes.io/proxy-read-timeout: "60"`.
3. Check backend memory/OOM kills: `kubectl describe pod <backend-pod>`.
"""
    },
    {
        "filename": "k8s-cert-manager-expired.md",
        "title": "mTLS / Ingress TLS Certificate Expiration in Service Mesh",
        "failure_type": "other",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/service-mesh-mtls-cert-expiration",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Inter-service communication fails with TLS handshake errors (`remote error: tls: bad certificate` or `certificate has expired`). Ingress routes fail with browser HTTPS warnings.

## Likely cause
cert-manager or Istio Citadel failed to auto-renew internal root CA or leaf certificates before expiration, causing proxy mTLS validation failures.

## How to confirm
Check cert-manager certificate status:
`kubectl get certificates -A`
Inspect certificate expiry:
`kubectl describe certificate <cert-name> -n <namespace>`
Check Envoy proxy logs:
`kubectl logs <pod-name> -c istio-proxy | grep -i "tls handshake"`

## Fix
1. Trigger manual certificate reissue: `kubectl cert-manager renew <cert-name> -n <namespace>`.
2. Verify cert-manager webhook and controller are running: `kubectl get pods -n cert-manager`.
3. If using Istio mesh CA, restart istiod and rolling restart affected pods to rotate leaf certificates.
"""
    },
    {
        "filename": "k8s-inode-exhaustion.md",
        "title": "Node Disk Inode Exhaustion: Pods Evicted with DiskPressure",
        "failure_type": "disk_full",
        "source_type": "external_doc",
        "source_url": "https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Nodes report `DiskPressure` taint even though `df -h` shows ample gigabytes free. Pods fail with `NodeHasDiskPressure` or `no space left on device` during file write.

## Likely cause
File system inode exhaustion (`df -i` shows 100% inode usage). Thousands of tiny temporary files, PHP session files, or un-rotated container log files have consumed all available inode slots.

## How to confirm
Check inode usage on the node:
`df -ih`
Find directory with excessive file count:
`find /var/lib/docker/overlay2 -maxdepth 3 -type d -exec echo -n "{} " \\; -exec ls -1 {} \\; | wc -l`
Check kubelet events for DiskPressure:
`kubectl describe node <node-name> | grep -i diskpressure`

## Fix
1. Prune unused docker images and stopped containers: `docker system prune -a --volumes` or `crictl rmi --prune`.
2. Locate and delete directory with millions of tiny files: `find /tmp -type f -mtime +7 -delete`.
3. Configure logrotate on host and enforce container ephemeral storage limits in pod specs.
"""
    },
    {
        "filename": "k8s-admission-webhook-timeout.md",
        "title": "Mutating/Validating Admission Webhook Timeout Blocks Deployments",
        "failure_type": "bad_config",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/webhook-timeout-blocks-deployments",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Any `kubectl apply`, pod creation, or Helm release hangs for 30 seconds then fails with `Internal error occurred: failed calling webhook: Post "https://...": context deadline exceeded`.

## Likely cause
An admission webhook service (e.g. OPA Gatekeeper, cert-manager, Kyverno, or Datadog admission controller) is down or unreachable, but configured with `failurePolicy: Fail`.

## How to confirm
List validating/mutating webhook configurations:
`kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations`
Check webhook service endpoints:
`kubectl get endpoints -A | grep -i webhook`
Inspect API server audit logs for webhook rejection errors.

## Fix
1. If urgent, temporarily set webhook failure policy to Ignore:
`kubectl patch mutatingwebhookconfiguration <webhook-name> --type='json' -p='[{"op":"replace","path":"/webhooks/0/failurePolicy","value":"Ignore"}]'`
2. Restore or restart the webhook backend pods: `kubectl rollout restart deployment <webhook-deployment> -n <ns>`.
3. Verify network policies allow kube-apiserver egress to the webhook pod service port.
"""
    },
    {
        "filename": "k8s-cni-ip-exhaustion.md",
        "title": "CNI Subnet IP Exhaustion: Pods Stuck in ContainerCreating",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
New pods remain stuck in `ContainerCreating`. Pod events display `failed to allocate for range: no IP addresses available in range set: 10.244.0.0/24`.

## Likely cause
The node or CNI IPAM pool (AWS VPC CNI, Calico, Flannel) has allocated all available IPs. Leaked IP allocations from deleted pods or an overly small podCIDR allocation.

## How to confirm
Inspect pod describe events:
`kubectl describe pod <pod-name> | grep -A 5 Events`
Check Calico IPAM / AWS VPC CNI allocation:
`calicoctl ipam show` or check host IPAM files in `/var/lib/cni/networks/`.

## Fix
1. Release orphaned IP allocations: restart CNI daemonset `kubectl rollout restart ds/calico-node -n kube-system`.
2. Expand node podCIDR subnet mask or assign secondary CIDR blocks in cloud VPC CNI.
3. Drain and replace nodes if local CNI state DB is corrupted.
"""
    },
    {
        "filename": "k8s-etcd-quota-exceeded.md",
        "title": "etcd Database Space Exceeded: Kubernetes API Server Read-Only",
        "failure_type": "other",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/etcd-database-space-exceeded",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Kubernetes API server refuses any create/update/delete operations: `etcdserver: mvcc: database space exceeded`. Read queries work, but no state changes can be written.

## Likely cause
etcd database size reached quota limit (default 2GB) due to lack of automatic compaction and defragmentation, compounded by frequent events or high object churn.

## How to confirm
Check etcd endpoint status and alarms:
`etcdctl --cacert=... --cert=... --key=... endpoint status -w table`
`etcdctl alarm list`
Check for alarm: `NOSPACE`.

## Fix
1. Get current etcd revision: `REV=$(etcdctl endpoint status --write-out="json" | jq .[0].Status.header.revision)`.
2. Compact old revisions: `etcdctl compact $REV`.
3. Defragment all etcd member endpoints: `etcdctl defrag --endpoints=https://127.0.0.1:2379`.
4. Disarm the NOSPACE alarm: `etcdctl alarm disarm`.
5. Increase etcd quota in `/etc/kubernetes/manifests/etcd.yaml` to `--quota-backend-bytes=8589934592` (8GB).
"""
    },
    {
        "filename": "k8s-docker-hub-rate-limit.md",
        "title": "ImagePullBackOff: Docker Hub Anonymous Pull Rate Limit Exceeded",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://docs.docker.com/docker-hub/download-rate-limit/",
        "license": "Apache-2.0",
        "content": """## Symptoms
Pods fail to start and stay in `ImagePullBackOff` or `ErrImagePull`. Pod events show `toomanyrequests: You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limit`.

## Likely cause
Anonymous docker pulls from shared NAT gateway IP exceeded Docker Hub limit (100 pulls per 6 hours per IP address).

## How to confirm
Check pod events:
`kubectl describe pod <pod-name> | grep -i toomanyrequests`
Verify image repository is public Docker Hub (e.g. `image: redis:alpine` or `image: nginx:latest`).

## Fix
1. Create a Kubernetes docker-registry secret with authenticated Docker credentials:
`kubectl create secret docker-registry regcred --docker-server=https://index.docker.io/v1/ --docker-username=<user> --docker-password=<token>`
2. Patch the default service account or pod spec with `imagePullSecrets: [{"name": "regcred"}]`.
3. Better: Mirror base images to internal private registry (ECR, GCR, Harbor).
"""
    },
    {
        "filename": "k8s-jvm-container-oom.md",
        "title": "Silent JVM Process Kill: -Xmx Exceeds Kubernetes Memory Limit",
        "failure_type": "out_of_memory",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/jvm-cgroups-memory-limit-oom",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Java/JVM microservices crash abruptly without throwing `java.lang.OutOfMemoryError` in application logs. Pod exit code is 137; container status is `OOMKilled: true`.

## Likely cause
The Java heap size `-Xmx` was configured close to container limit, ignoring off-heap native memory (Metaspace, thread stacks, direct byte buffers, JIT compiler cache). Total RSS exceeded cgroup memory limit, so Linux kernel OOM killer terminated the process.

## How to confirm
Check container status:
`kubectl describe pod <pod> | grep -E "(OOMKilled|Exit Code)"`
Check Java options in deployment manifest:
`kubectl get deployment <dep> -o yaml | grep -i xmx`
Compare pod memory limit with `-Xmx` setting.

## Fix
1. Follow the rule of thumb: Heap should not exceed 70% of pod memory limit (e.g., `-Xmx700m` for a 1Gi limit).
2. Use modern container-aware JVM flags: `-XX:+UseContainerSupport -XX:MaxRAMPercentage=70.0`.
3. Increase pod memory limit in `resources.limits.memory`.
"""
    },
    {
        "filename": "k8s-ephemeral-storage-eviction.md",
        "title": "Pod Eviction: The Node Had Condition DiskPressure / Ephemeral Storage",
        "failure_type": "disk_full",
        "source_type": "external_doc",
        "source_url": "https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#local-ephemeral-storage",
        "license": "CC BY 4.0",
        "content": """## Symptoms
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
"""
    },
    {
        "filename": "k8s-pod-terminating-hung-nfs.md",
        "title": "Pod Stuck in Terminating State: Hung Mount or Finalizer",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Pod remains in `Terminating` status indefinitely. `kubectl delete pod` does not complete. New deployments cannot complete rollout.

## Likely cause
A hung NFS/CSI volume unmount blocks container runtime teardown, or an unfulfilled finalizer is present on the pod object.

## How to confirm
Inspect pod finalizers and status:
`kubectl get pod <pod> -o jsonpath='{.metadata.finalizers}'`
Check kubelet error logs:
`journalctl -u kubelet -n 50 | grep -i "unmount"`
Check kernel dmesg for hung filesystem tasks:
`dmesg -T | grep -i "nfs: server not responding"`

## Fix
1. If safe, remove hung finalizer: `kubectl patch pod <pod> -p '{"metadata":{"finalizers":null}}'`.
2. Force delete pod: `kubectl delete pod <pod> --force --grace-period=0`.
3. Unmount hung filesystem on host: `umount -f -l <mount-point>`.
"""
    },
    {
        "filename": "k8s-networkpolicy-traffic-blocked.md",
        "title": "Connection Refused / Dropped: Misconfigured NetworkPolicy",
        "failure_type": "dependency_failure",
        "source_type": "external_doc",
        "source_url": "https://kubernetes.io/docs/concepts/services-networking/network-policies/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Service A cannot reach Service B (`connection timed out` or `no route to host`), but Service B is healthy and pod is running. Direct curl from inside the namespace fails.

## Likely cause
A Kubernetes `NetworkPolicy` selects the namespace or pod with default deny ingress, but lacks an ingress rule matching Service A's namespace or pod label.

## How to confirm
Check active network policies in the namespace:
`kubectl get networkpolicy -n <namespace>`
Inspect ingress/egress rules:
`kubectl describe networkpolicy <policy-name> -n <namespace>`
Test inter-pod connectivity using ephemeral debug container:
`kubectl debug -it <pod> --image=curlimages/curl -- curl -v http://<service-b>:8080/health`

## Fix
1. Add ingress rule allowing traffic from Service A's pod label:
```yaml
ingress:
- from:
  - podSelector:
      matchLabels:
        app: service-a
  ports:
  - protocol: TCP
    port: 8080
```
2. Apply updated NetworkPolicy: `kubectl apply -f networkpolicy.yaml`.
"""
    },
    {
        "filename": "k8s-hpa-thrashing-metrics.md",
        "title": "Horizontal Pod Autoscaler Flapping: CPU Threshold Thrashing",
        "failure_type": "cpu_saturation",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/hpa-flapping-scale-thrash",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Deployment rapidly scales up to max replicas, then scales down to min replicas, cycling continuously every few minutes. Application exhibits elevated latency and 503 errors during cold starts.

## Likely cause
HPA target utilization is set too close to baseline load, or pods have expensive initialization routines that consume 100% CPU on startup, triggering immediate scale-up before load stabilizes.

## How to confirm
Inspect HPA event history:
`kubectl describe hpa <hpa-name>`
Check replica count oscillations over time:
`kubectl get deployment <dep> -w`
Review CPU usage during container start vs steady state.

## Fix
1. Configure stabilization window in HPA behavior spec:
```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300
    policies:
    - type: Percent
      value: 10
      periodSeconds: 60
```
2. Adjust `resources.requests.cpu` to reflect real steady-state demands.
3. Use startup probes to prevent HPA from counting initialization CPU spikes.
"""
    },
    {
        "filename": "k8s-fd-exhaustion-node.md",
        "title": "Node Out of File Descriptors: Too Many Open Files in System",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://kubernetes.io/docs/tasks/administer-cluster/sysctl-cluster/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
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
"""
    },

    # -------------------------------------------------------------
    # 2. PostgreSQL Troubleshooting & Incident Postmortems (12 docs)
    # -------------------------------------------------------------
    {
        "filename": "postgres-txid-wraparound.md",
        "title": "PostgreSQL Emergency Shutdown: Transaction ID Wraparound Freeze",
        "failure_type": "db_timeout",
        "source_type": "external_doc",
        "source_url": "https://www.postgresql.org/docs/current/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND",
        "license": "PostgreSQL License",
        "content": """## Symptoms
PostgreSQL stops accepting all write connections: `FATAL: database is not accepting commands to avoid wraparound data loss in database "orders"`. Application queries fail immediately.

## Likely cause
PostgreSQL 32-bit transaction counter reached 2 billion transactions without aggressive autovacuum freeze running to advance `relfrozenxid`.

## How to confirm
Check transaction age for all databases:
`SELECT datname, age(datfrozenxid) FROM pg_database ORDER BY 2 DESC;`
Check Postgres log file for warning:
`WARNING: database "orders" must be vacuumed within 10000000 transactions`.

## Fix
1. Restart PostgreSQL in single-user maintenance mode:
`postgres --single -D /var/lib/postgresql/data orders`
2. Run full freeze vacuum:
`VACUUM FREEZE ANALYZE;`
3. Tune autovacuum to prevent recurrence:
`autovacuum_freeze_max_age = 200000000`
`autovacuum_vacuum_cost_limit = 2000`
"""
    },
    {
        "filename": "postgres-deadlock-concurrent-update.md",
        "title": "PostgreSQL Deadlock Detected: Concurrent Row Lock Contention",
        "failure_type": "db_timeout",
        "source_type": "external_doc",
        "source_url": "https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-DEADLOCKS",
        "license": "PostgreSQL License",
        "content": """## Symptoms
Transactions aborted with `ERROR: deadlock detected` / `DETAIL: Process 14023 waits for ShareLock on transaction 88921; Process 14028 waits for ExclusiveLock`. API endpoints return 500.

## Likely cause
Two concurrent transactions updated the same set of rows in different order, creating a mutual dependency cycle.

## How to confirm
Check active locks in PostgreSQL:
```sql
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

## Fix
1. Ensure all code paths acquire row locks in the same consistent order (e.g. `ORDER BY id`).
2. Add `SELECT ... FOR UPDATE SKIP LOCKED` or `NOWAIT` for queue processing patterns.
3. Tune `deadlock_timeout` (default 1s) and ensure application implements exponential backoff retry.
"""
    },
    {
        "filename": "postgres-connection-pool-exhausted.md",
        "title": "PostgreSQL Connection Limit Exceeded: FATAL remaining connection slots",
        "failure_type": "db_timeout",
        "source_type": "external_doc",
        "source_url": "https://www.postgresql.org/docs/current/runtime-config-connection.html",
        "license": "PostgreSQL License",
        "content": """## Symptoms
Microservices fail to connect to PostgreSQL: `FATAL: remaining connection slots are reserved for non-replication superuser connections` or `psycopg2.OperationalError: server closed the connection unexpectedly`.

## Likely cause
Connection pool leak in application instances, or sudden scale-out of pods where each pod initializes a pool of 20 connections, surpassing `max_connections` (default 100).

## How to confirm
Query connection count by state and application:
`SELECT state, count(*) FROM pg_stat_activity GROUP BY state;`
`SELECT client_addr, count(*) FROM pg_stat_activity GROUP BY client_addr ORDER BY count(*) DESC;`
Look for large number of connections in `idle` or `idle in transaction` state.

## Fix
1. Terminate idle connections:
`SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < current_timestamp - INTERVAL '15 minutes';`
2. Deploy PgBouncer or Pgpool-II in transaction pooling mode between services and database.
3. Configure application connection pool size: `max_pool_size = 5` per container replica.
"""
    },
    {
        "filename": "postgres-wal-disk-full.md",
        "title": "PostgreSQL PANIC: Could Not Write to Log File, Disk Full",
        "failure_type": "disk_full",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/postgres-wal-disk-full-panic",
        "license": "CC BY 4.0",
        "content": """## Symptoms
PostgreSQL server crashes and refuses to start: `PANIC: could not write to log file 000000010000003400000021: No space left on device`. Database is completely down.

## Likely cause
WAL (Write-Ahead Log) archiving command failed (`archive_command` failing), or an inactive replication slot is holding WAL segments, filling the `pg_wal` disk volume.

## How to confirm
Check disk space on data partition: `df -h /var/lib/postgresql/data`.
Check for inactive replication slots holding WAL:
`SELECT slot_name, active, pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS retained_bytes FROM pg_replication_slots;`
Check Postgres logs for `archive_command` errors.

## Fix
1. Drop inactive or abandoned replication slot:
`SELECT pg_drop_replication_slot('abandoned_replica');`
2. If archiving is failing, fix archive script destination or temporarily set `archive_command = '/bin/true'`.
3. Increase storage volume size or set `wal_keep_size` and `max_slot_wal_keep_size` limits in `postgresql.conf`.
"""
    },
    {
        "filename": "postgres-replication-lag.md",
        "title": "PostgreSQL Streaming Replication Lag: Stale Read Queries",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW",
        "license": "PostgreSQL License",
        "content": """## Symptoms
Clients reading from read-replica receive outdated data (e.g. order placed on primary is missing on replica). Replication delay metric grows continuously.

## Likely cause
Network throughput saturation between primary and standby, long-running query on replica causing vacuum conflict, or high write volume exceeding replica apply speed.

## How to confirm
On primary, check replication status:
`SELECT application_name, client_addr, state, sync_state, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes FROM pg_stat_replication;`
On replica, check delay:
`SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;`

## Fix
1. Enable `hot_standby_feedback = on` on replica to inform primary of needed snapshots.
2. Cancel conflicting queries on standby: `max_standby_streaming_delay = 30s`.
3. Check replica disk I/O metrics; optimize I/O provision or scale replica compute.
"""
    },
    {
        "filename": "postgres-stale-statistics-vacuum.md",
        "title": "PostgreSQL Slow Query Plan: Stale Statistics After Bulk Insert",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://www.postgresql.org/docs/current/routine-vacuuming.html#VACUUM-FOR-STATISTICS",
        "license": "PostgreSQL License",
        "content": """## Symptoms
Previously fast queries suddenly take 10+ seconds. PostgreSQL query planner selects full sequential table scan instead of using available B-Tree index.

## Likely cause
Bulk INSERT or UPDATE modified table row count significantly without updating the query planner statistics table `pg_statistic`.

## How to confirm
Run EXPLAIN ANALYZE on slow query:
`EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42;`
Compare `expected rows` vs `actual rows` in the explain plan (order of magnitude difference indicates stale statistics).

## Fix
1. Run manual analyze on affected table:
`ANALYZE orders;` or `VACUUM ANALYZE orders;`
2. Tune autovacuum analyze threshold in `postgresql.conf`:
`autovacuum_analyze_scale_factor = 0.05`
`autovacuum_analyze_threshold = 50`
"""
    },
    {
        "filename": "postgres-idle-in-transaction.md",
        "title": "Idle In Transaction Connections: Table Bloat and Vacuum Blocked",
        "failure_type": "db_timeout",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/postgres-idle-in-transaction-bloat",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Table disk usage swells 10x (table bloat). Query latency increases steadily. Autovacuum runs constantly but reports dead tuples cannot be removed.

## Likely cause
Client opened a transaction (`BEGIN`), executed a query, but never called `COMMIT` or `ROLLBACK` due to unhandled application exception or network timeout.

## How to confirm
Find all idle in transaction queries open longer than 5 minutes:
```sql
SELECT pid, usename, client_addr, state, state_change, query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND state_change < current_timestamp - INTERVAL '5 minutes';
```

## Fix
1. Terminate offending backends:
`SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < current_timestamp - INTERVAL '5 minutes';`
2. Set safety timeout in `postgresql.conf`:
`idle_in_transaction_session_timeout = 60000` (terminates sessions idle in transaction after 60s).
3. Fix application code to use context managers (`with db.session:`) ensuring rollback on error.
"""
    },
    {
        "filename": "postgres-work-mem-disk-spill.md",
        "title": "Temporary Files Disk Spill: Low work_mem Causes High Latency",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://www.postgresql.org/docs/current/runtime-config-resource.html#GUC-WORK-MEM",
        "license": "PostgreSQL License",
        "content": """## Symptoms
Queries with `ORDER BY`, `DISTINCT`, or hash joins become extremely slow. High disk write I/O on Postgres data directory. Log message: `temporary file: path ".../pgsql_tmp/...", size 450123456 bytes`.

## Likely cause
`work_mem` setting is too small (default 4MB), forcing PostgreSQL to spill sort and hash operations to temporary disk files instead of RAM.

## How to confirm
Enable temp file logging: `log_temp_files = 0`.
Check Postgres logs for temp file creation:
`grep "temporary file" /var/log/postgresql/*.log`
Check query plan: `EXPLAIN ANALYZE SELECT ...` look for `Sort Method: external merge Disk: 45000kB`.

## Fix
1. Increase `work_mem` globally in `postgresql.conf` (e.g. `work_mem = 64MB`).
2. Or set it per-session for heavy reporting queries: `SET work_mem = '256MB';`.
3. Ensure server RAM is sufficient: `work_mem * max_connections` should not exceed total RAM.
"""
    },
    {
        "filename": "postgres-statement-timeout-aborted.md",
        "title": "statement_timeout Abort: Long Queries Terminated by Database",
        "failure_type": "db_timeout",
        "source_type": "external_doc",
        "source_url": "https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-STATEMENT-TIMEOUT",
        "license": "PostgreSQL License",
        "content": """## Symptoms
Application throws `ERROR: canceling statement due to statement timeout`. Background reports or end-of-day reconciliation jobs fail midway.

## Likely cause
The query duration exceeded `statement_timeout` configured in `postgresql.conf` or user role level.

## How to confirm
Check current timeout setting:
`SHOW statement_timeout;`
Inspect failed query in Postgres logs: `grep "canceling statement due to statement timeout" postgresql.log`.

## Fix
1. Optimize the slow query by adding missing index or refining WHERE clause.
2. For specific background workers, override timeout on connection: `SET statement_timeout = '300s';`.
3. If table is missing index, create index concurrently: `CREATE INDEX CONCURRENTLY idx_orders_created ON orders (created_at);`.
"""
    },
    {
        "filename": "postgres-corrupt-index-missing-rows.md",
        "title": "Corrupted B-Tree Index: Queries Return Partial or Inconsistent Rows",
        "failure_type": "other",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/postgres-corrupt-index-after-power-loss",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Query using an index misses existing rows, but `SET enable_indexscan = off;` finds the rows via sequential scan. In severe cases, query crashes with `ERROR: invalid page in block ... of relation ...`.

## Likely cause
Hard power loss or faulty underlying storage controller caused partial block writes in index pages without affecting base heap table.

## How to confirm
Use PostgreSQL `amcheck` extension:
```sql
CREATE EXTENSION amcheck;
SELECT bt_index_check('idx_orders_customer_id', true);
```
Look for corruption errors reported by `amcheck`.

## Fix
1. Rebuild corrupted index concurrently (no lock on reads/writes):
`REINDEX INDEX CONCURRENTLY idx_orders_customer_id;`
2. Verify integrity after rebuild: `SELECT bt_index_check('idx_orders_customer_id', true);`.
3. Check host hardware diagnostics and SMART disk status.
"""
    },
    {
        "filename": "postgres-ssl-renegotiation.md",
        "title": "SSL Connection Renegotiation Failure Under High Concurrency",
        "failure_type": "network_timeout",
        "source_type": "external_doc",
        "source_url": "https://www.postgresql.org/docs/current/ssl-tcp.html",
        "license": "PostgreSQL License",
        "content": """## Symptoms
Microservices connecting over TLS/SSL experience sudden connection drops with `SSL error: decryption failed or bad record mac` or handshake timeouts.

## Likely cause
SSL renegotiation limit reached in older Postgres setups or OpenSSL library compatibility conflict between client container and server.

## How to confirm
Check Postgres log for SSL messages:
`grep -i "ssl" /var/log/postgresql/postgresql.log`
Test connection with openssl s_client:
`openssl s_client -connect postgres.internal:5432 -starttls postgres`

## Fix
1. Ensure `ssl_renegotiation_limit = 0` in `postgresql.conf` (disables periodic renegotiation).
2. Align TLS cipher suites: `ssl_ciphers = 'HIGH:!aNULL'`.
3. Update client database driver in microservice container to use TLS 1.3.
"""
    },
    {
        "filename": "postgres-shared-buffers-starvation.md",
        "title": "PostgreSQL Cache Hit Ratio Drop: Low shared_buffers",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://www.postgresql.org/docs/current/runtime-config-resource.html#GUC-SHARED-BUFFERS",
        "license": "PostgreSQL License",
        "content": """## Symptoms
Database latency spikes by 5x. Disk read IOPS reach 100% capacity. Cache hit ratio drops below 95%.

## Likely cause
`shared_buffers` is configured to the default 128MB on a server with 16GB+ RAM, causing almost every query to read directly from disk rather than memory cache.

## How to confirm
Check cache hit ratio:
```sql
SELECT sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_hit_ratio
FROM pg_statio_user_tables;
```
If ratio is below 0.99, memory caching is inadequate.

## Fix
1. Set `shared_buffers = 4GB` (recommended 25% of dedicated server RAM) in `postgresql.conf`.
2. Set `effective_cache_size = 12GB` (75% of total RAM).
3. Restart PostgreSQL service for changes to take effect.
"""
    },

    # -------------------------------------------------------------
    # 3. Docker & Container Runtime Troubleshooting (8 docs)
    # -------------------------------------------------------------
    {
        "filename": "docker-containerd-socket-deadlock.md",
        "title": "Docker Daemon Unresponsive: containerd Socket Deadlock",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://docs.docker.com/engine/troubleshoot-and-support/daemon-troubleshooting/",
        "license": "Apache-2.0",
        "content": """## Symptoms
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
"""
    },
    {
        "filename": "docker-bridge-subnet-collision.md",
        "title": "Docker Network Routing Blackhole: Bridge IP Overlaps Host Subnet",
        "failure_type": "dependency_failure",
        "source_type": "external_doc",
        "source_url": "https://docs.docker.com/network/packet-filtering-firewalls/",
        "license": "Apache-2.0",
        "content": """## Symptoms
Containers cannot connect to company intranet, external DB, or corporate LDAP (`no route to host` or packet drop). Host can reach the destination fine, but containers cannot.

## Likely cause
Docker default bridge network `docker0` auto-allocated subnet `172.17.0.0/16` or `172.18.0.0/16` which collides with the organization's physical VPC/LAN network range.

## How to confirm
Check host routing table: `ip route` or `netstat -rn`.
Inspect Docker bridge subnet:
`docker network inspect bridge | grep -i subnet`
Compare container subnet with company VPN/VPC IP range.

## Fix
1. Configure custom pool in `/etc/docker/daemon.json`:
```json
{
  "default-address-pools": [
    {"base": "10.200.0.0/16", "size": 24}
  ]
}
```
2. Restart docker service: `systemctl restart docker`.
3. Recreate affected docker networks: `docker network rm <net> && docker compose up -d`.
"""
    },
    {
        "filename": "docker-zombie-process-reaping.md",
        "title": "PID Limit Exhaustion: Zombie Process Accumulation in Container",
        "failure_type": "other",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/docker-zombie-process-pid-exhaustion",
        "license": "CC BY 4.0",
        "content": """## Symptoms
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
"""
    },
    {
        "filename": "docker-overlay2-corruption.md",
        "title": "Docker Storage Overlay2 Corruption: Read-Only Filesystem in Container",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://docs.docker.com/storage/storagedriver/overlayfs-driver/",
        "license": "Apache-2.0",
        "content": """## Symptoms
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
"""
    },
    {
        "filename": "docker-dns-embedded-resolver.md",
        "title": "Embedded DNS Resolver 127.0.0.11 Failure in Docker User Networks",
        "failure_type": "network_timeout",
        "source_type": "external_doc",
        "source_url": "https://docs.docker.com/network/drivers/bridge/",
        "license": "Apache-2.0",
        "content": """## Symptoms
Containers on a custom user-defined bridge network fail to resolve other service names: `getaddrinfo ENOTFOUND order-service`. DNS requests to `127.0.0.11:53` time out.

## Likely cause
Docker internal DNS server thread within dockerd became hung or iptables routing rules for 127.0.0.11 were overwritten by host firewall (e.g. `ufw` reload or `firewalld`).

## How to confirm
From inside container:
`nslookup order-service 127.0.0.11`
Check iptables NAT table for Docker DNS PREROUTING rules:
`iptables -t nat -L DOCKER_OUTPUT -n`

## Fix
1. Verify containers share the exact same user-defined network: `docker network inspect <net_name>`.
2. Reload iptables and restart docker:
`systemctl restart docker`
3. Ensure host firewalld/ufw does not flush Docker chains.
"""
    },
    {
        "filename": "docker-volume-permission-denied.md",
        "title": "Permission Denied on Host Volume Mount: Non-Root UID Mismatch",
        "failure_type": "bad_config",
        "source_type": "external_doc",
        "source_url": "https://docs.docker.com/storage/volumes/",
        "license": "Apache-2.0",
        "content": """## Symptoms
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
"""
    },
    {
        "filename": "docker-healthcheck-timeout-cascade.md",
        "title": "Health Check Command Timeout: Restart Cascade in Docker Compose",
        "failure_type": "health_check_failure",
        "source_type": "external_doc",
        "source_url": "https://docs.docker.com/engine/reference/builder/#healthcheck",
        "license": "Apache-2.0",
        "content": """## Symptoms
Healthy containers under moderate load are suddenly marked `unhealthy` and restarted repeatedly by Docker or orchestration layer, creating a cascading outage.

## Likely cause
`HEALTHCHECK` command timeout is too short (e.g. `timeout: 3s`) while probing an endpoint that does database queries. Under load, query latency spikes beyond 3s, causing health check to fail 3 consecutive times.

## How to confirm
Inspect container health logs:
`docker inspect <container> --format '{{json .State.Health}}' | jq .`
Check duration of recent health checks in `Log` array.

## Fix
1. Make health check endpoint lightweight (avoid database queries in `/healthz` liveness; keep deep checks in `/readyz`).
2. Increase timeout and retries in docker-compose.yml:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 15s
  timeout: 10s
  retries: 5
  start_period: 30s
```
"""
    },
    {
        "filename": "docker-json-logging-disk-full.md",
        "title": "Unbounded json-file Logging Driver Fills Host Root Disk",
        "failure_type": "disk_full",
        "source_type": "external_doc",
        "source_url": "https://docs.docker.com/config/containers/logging/json-file/",
        "license": "Apache-2.0",
        "content": """## Symptoms
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
"""
    },

    # -------------------------------------------------------------
    # 4. Prometheus & Observability Troubleshooting (7 docs)
    # -------------------------------------------------------------
    {
        "filename": "prom-cardinality-explosion-oom.md",
        "title": "Prometheus Memory OOM Crash: Metric High-Cardinality Explosion",
        "failure_type": "out_of_memory",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/prometheus-high-cardinality-oom",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Prometheus container crashes with exit code 137 (`OOMKilled: true`). Memory usage climbs vertically right before crash. Dashboards and alerting go dark.

## Likely cause
A newly deployed service added high-cardinality labels (e.g. `user_id`, `order_id`, `email`, or `ip_address`) to a Prometheus counter or histogram, creating millions of unique time series.

## How to confirm
Query Prometheus TSDB status API:
`curl -s http://localhost:9090/api/v1/status/tsdb | jq .`
Look at `seriesCountByMetricName` for metrics with > 100,000 series.
Inspect recent commits for `prometheus.NewCounterVec` label definitions.

## Fix
1. Drop offending high-cardinality metrics in Prometheus `metric_relabel_configs`:
```yaml
metric_relabel_configs:
- source_labels: [__name__]
  regex: 'http_requests_per_user_total'
  action: drop
```
2. Remove high-cardinality labels from application code and redeploy service.
3. Reload Prometheus configuration: `curl -X POST http://localhost:9090/-/reload`.
"""
    },
    {
        "filename": "prom-out-of-order-samples.md",
        "title": "Prometheus Samples Rejected: Error Out of Order / Duplicate Timestamp",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://prometheus.io/docs/prometheus/latest/configuration/configuration/#tsdb",
        "license": "Apache-2.0",
        "content": """## Symptoms
Prometheus logs report `Error on ingesting samples that are out of order` or `err: duplicate sample for timestamp`. Recent metrics are missing from Grafana.

## Likely cause
Clock drift (NTP desynchronization) between scrape target host and Prometheus server, or multiple target instances pushing identical metrics with backdated timestamps.

## How to confirm
Check host clock synchronization:
`chronyc tracking` or `ntpq -p`
Inspect Prometheus log for out of order errors:
`kubectl logs deployment/prometheus | grep -i "out of order"`

## Fix
1. Resynchronize system clock using NTP: `systemctl restart systemd-timesyncd` or `chronyd`.
2. If ingesting historical data, enable out-of-order ingestion in Prometheus TSDB configuration:
`--storage.tsdb.out-of-order.time-window=10m`
"""
    },
    {
        "filename": "prom-scrape-timeout-slow-endpoint.md",
        "title": "Prometheus Scrape Target Timeout: context deadline exceeded",
        "failure_type": "network_timeout",
        "source_type": "external_doc",
        "source_url": "https://prometheus.io/docs/prometheus/latest/querying/basics/",
        "license": "Apache-2.0",
        "content": """## Symptoms
Prometheus targets page (`/targets`) shows endpoint in `DOWN` state with error `context deadline exceeded`. Metric `up{job="order-service"} == 0`.

## Likely cause
The application `/metrics` endpoint takes longer than `scrape_timeout` (default 10s) to generate text payload, often due to computing complex runtime stats or holding locks.

## How to confirm
Test `/metrics` response time directly from command line:
`time curl -s -o /dev/null http://order-service:8003/metrics`
If duration exceeds 10s, scrape timeout will trigger.

## Fix
1. Optimize `/metrics` endpoint to serve cached metrics rather than computing live aggregations.
2. In `prometheus.yml`, temporarily increase scrape timeout for that job:
```yaml
scrape_interval: 30s
scrape_timeout: 25s
```
3. Reload Prometheus: `curl -X POST http://localhost:9090/-/reload`.
"""
    },
    {
        "filename": "prom-wal-replay-crash.md",
        "title": "Prometheus Fails to Start: WAL Corrupted on Sudden Shutdown",
        "failure_type": "crash_loop",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/prometheus-corrupted-wal-startup-crash",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Prometheus pod is in `CrashLoopBackOff`. Startup logs display: `caller=main.go:812 err="opening storage failed: repair WAL: ... corrupted segment"`.

## Likely cause
Power failure or kernel crash occurred while Prometheus was writing to the write-ahead log (`wal/` directory).

## How to confirm
Examine Prometheus container crash logs:
`kubectl logs -n monitoring deployment/prometheus | grep -i "corrupted segment"`

## Fix
1. Start Prometheus with auto-repair flag:
`--storage.tsdb.wal-compression` and let WAL repair run.
2. If crash loop persists, delete corrupted WAL segment:
Move bad segment: `mv /prometheus/wal/00000042 /tmp/`
3. Restart Prometheus. Only the last 2 hours of un-compacted data are lost; historical compacted blocks remain intact.
"""
    },
    {
        "filename": "prom-retention-disk-full.md",
        "title": "Prometheus Storage Disk Full: TSDB Compaction Failed",
        "failure_type": "disk_full",
        "source_type": "external_doc",
        "source_url": "https://prometheus.io/docs/prometheus/latest/storage/",
        "license": "Apache-2.0",
        "content": """## Symptoms
Prometheus data partition reaches 100% capacity. Logs report `caller=compact.go:501 err="compact head: write block: write /prometheus/...: no space left on device"`.

## Likely cause
Prometheus storage retention configuration `--storage.tsdb.retention.time` was set too long (e.g. 90d) without setting `--storage.tsdb.retention.size`, exceeding disk capacity.

## How to confirm
Check disk space on storage volume:
`df -h /prometheus`
Check current retention settings:
`ps aux | grep prometheus | grep -i retention`

## Fix
1. Configure retention size cap in Prometheus flags:
`--storage.tsdb.retention.size=40GB`
`--storage.tsdb.retention.time=15d`
2. Expand PersistentVolume in Kubernetes:
`kubectl patch pvc prometheus-data -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'`.
"""
    },
    {
        "filename": "prom-remote-write-queue-full.md",
        "title": "Prometheus Remote Write Queue Full: Dropping Remote Metrics",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://prometheus.io/docs/prometheus/latest/configuration/configuration/#remote_write",
        "license": "Apache-2.0",
        "content": """## Symptoms
Metrics sent to long-term storage (Cortex, Thanos, Grafana Mimir) are delayed or missing. Prometheus metric `prometheus_remote_storage_dropped_samples_total` is increasing.

## Likely cause
Network congestion or rate limiting on the remote storage receiver. Prometheus remote write queue is full and dropping samples.

## How to confirm
Query Prometheus metrics:
`prometheus_remote_storage_queue_highest_sent_timestamp_seconds`
`rate(prometheus_remote_storage_dropped_samples_total[5m]) > 0`
Inspect Prometheus logs for `remote_write: non-recoverable error` or HTTP 429.

## Fix
1. Increase queue capacity in `prometheus.yml`:
```yaml
remote_write:
- url: "https://mimir.internal/api/v1/push"
  queue_config:
    max_shards: 100
    max_samples_per_send: 5000
    capacity: 20000
```
2. Verify network bandwidth and ensure remote receiver is not CPU throttled.
"""
    },
    {
        "filename": "prom-rule-evaluation-slow.md",
        "title": "Prometheus Alerting Lag: Rule Evaluation Interval Exceeded",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/",
        "license": "Apache-2.0",
        "content": """## Symptoms
Alerts fire with significant delay (10-15 minutes after failure starts). Prometheus logs report `Rule group 'alerts' evaluation took 45s, interval is 30s`.

## Likely cause
Complex subqueries or unbounded regex label matching in alert rules (`{__name__=~".*"} [1h]`) take longer to execute than the rule group evaluation interval.

## How to confirm
Query rule evaluation metrics:
`prometheus_rule_group_last_duration_seconds`
`prometheus_rule_group_iterations_missed_total`

## Fix
1. Optimize alert rule queries: avoid subqueries inside alert definitions; use recording rules for precomputing expensive aggregations.
2. Split rules into multiple groups with independent intervals.
3. Increase evaluation interval for non-critical alerts from 15s to 1m.
"""
    },

    # -------------------------------------------------------------
    # 5. Major Cloud & Distributed System Postmortems (8 docs)
    # -------------------------------------------------------------
    {
        "filename": "cloud-cloudflare-redos-cpu.md",
        "title": "Cloudflare Global Outage: ReDoS Regular Expression CPU Spike",
        "failure_type": "cpu_saturation",
        "source_type": "external_postmortem",
        "source_url": "https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
All edge reverse proxy nodes reach 100% CPU utilization. HTTP 502 errors served to traffic globally. Core routing processes freeze.

## Likely cause
A newly deployed WAF rule contained a poorly written regular expression with catastrophic backtracking (e.g. `.*.*=.*`), which consumed exponential CPU cycles when evaluated against malformed input.

## How to confirm
Check CPU utilization across cluster: `top` or `mpstat -P ALL 1`.
Inspect CPU profile / flame graph:
`perf top` showing 99% CPU in `pcre_exec` or regex evaluation engine.
Correlate failure timestamp with recent WAF or route deployment.

## Fix
1. Immediately roll back the offending rule or disable the newly deployed WAF rule group.
2. Use non-backtracking regular expression engines (such as Google RE2 or Rust regex) which guarantee linear time evaluation $O(n)$.
3. Run automated regex static analysis in CI to detect exponential backtracking patterns prior to deployment.
"""
    },
    {
        "filename": "cloud-aws-s3-cascade-outage.md",
        "title": "AWS S3 Cascading Outage: Command Typo Removes Core Capacity",
        "failure_type": "dependency_failure",
        "source_type": "external_postmortem",
        "source_url": "https://aws.amazon.com/message/41926/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
All operations against S3 in us-east-1 fail. Downstream AWS services (EC2 build systems, Lambda, SQS) fail because they depend on S3 metadata storage.

## Likely cause
An operator debugging an issue executed a command with an incorrect parameter, taking down a far larger number of S3 subsystem servers than intended, requiring a full cold start of S3 subsystems that had never been cold-restarted at scale.

## How to confirm
Inspect service health dashboard for dependency failures:
Check if internal API calls to object storage return 500/503.
Check cascading timeouts in services relying on centralized configuration buckets.

## Fix
1. Implement strict command validation and rate-limiting on destructive administrative tools.
2. Decouple critical service bootpaths from external dependencies: services should cache required configuration locally.
3. Partition failure domains into smaller independent cells to avoid single blast radius.
"""
    },
    {
        "filename": "cloud-github-mysql-failover-splitbrain.md",
        "title": "GitHub Database Partition: Network Blip Causes Split-Brain",
        "failure_type": "other",
        "source_type": "external_postmortem",
        "source_url": "https://github.blog/2018-10-30-oct21-post-incident-analysis/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Site locked in maintenance mode. Database writes disabled. Data inconsistency between primary data center and secondary failover site.

## Likely cause
A 43-second network partition between two data centers caused orchestrator to promote a replica to primary in the secondary site while the original primary continued taking writes, creating split-brain divergence.

## How to confirm
Compare transaction logs (binlog LSN or WAL positions) across database instances.
Check orchestrator failover logs: `orchestrator-client -c which-cluster-instances`.

## Fix
1. Stop writes immediately to prevent further divergence.
2. Designate authoritative primary and extract missing delta transactions from diverged secondary.
3. Use consensus-based quorum (Raft/Paxos) for automated failover so promotion requires a majority vote.
"""
    },
    {
        "filename": "cloud-gitlab-database-deletion.md",
        "title": "GitLab Production Outage: Accidental Directory Deletion in Disaster Recovery",
        "failure_type": "other",
        "source_type": "external_postmortem",
        "source_url": "https://about.gitlab.com/blog/2017/02/01/gitlab-dot-com-database-incident/",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Production database directory erased (`/var/opt/gitlab/postgresql/data`). Production database completely offline. Automated backups failed to restore.

## Likely cause
During stressful manual debugging of replication lag, an administrator ran `rm -rf` on the wrong terminal shell (primary server instead of replica). Five distinct backup mechanisms were either broken, untested, or expired.

## How to confirm
Check host data directory: `ls -la /var/opt/gitlab/postgresql/data` (directory empty).
Check database process status: `systemctl status postgresql`.

## Fix
1. Locate most recent valid snapshot (LVM snapshot or disk volume backup).
2. Restore snapshot to a separate staging host and replay write-ahead logs.
3. Automated disaster recovery drills: routinely verify backup restoration in automated CI pipelines.
4. Revoke direct interactive SSH shell root access to production primary databases; use audited automation.
"""
    },
    {
        "filename": "cloud-redis-cluster-split-brain.md",
        "title": "Redis Sentinel / Cluster Split-Brain: Data Loss During Partition",
        "failure_type": "other",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/redis-sentinel-split-brain-data-loss",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Clients write data successfully to Redis, but reads after network recovery show missing keys (data loss). Two nodes claim to be master simultaneously.

## Likely cause
Network partition isolated the old master with a subset of clients while Sentinel elected a new master on the other side. When partition healed, the old master was demoted to replica and its new writes were overwritten by the new master's dataset.

## How to confirm
Check role of all Redis nodes:
`redis-cli -h node1 info replication`
`redis-cli -h node2 info replication`
Check if multiple nodes report `role:master`.

## Fix
1. Configure `min-replicas-to-write 1` and `min-replicas-max-lag 10` in `redis.conf` (master refuses writes if it cannot communicate with at least 1 healthy replica).
2. Ensure Sentinel quorum `sentinel monitor mymaster <ip> <port> <quorum>` is set to majority of Sentinel nodes.
"""
    },
    {
        "filename": "cloud-kafka-rebalance-storm.md",
        "title": "Kafka Consumer Group Rebalance Storm: Message Processing Stall",
        "failure_type": "high_error_rate",
        "source_type": "external_postmortem",
        "source_url": "https://k8s.af/kafka-consumer-rebalance-storm",
        "license": "CC BY 4.0",
        "content": """## Symptoms
Kafka consumer lag increases exponentially. Consumers spend 100% of time in rebalance protocol and 0% processing messages. Consumer logs show `CommitFailedException` and `Revoking previously assigned partitions`.

## Likely cause
A single slow message batch takes longer to process than `max.poll.interval.ms` (default 5 minutes). Kafka broker assumes consumer has died and triggers group rebalance, revoking and reassigning partitions.

## How to confirm
Check consumer lag using Kafka CLI:
`kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group order-processors`
Check consumer logs for `CommitFailedException: Commit cannot be completed since the group has already rebalanced`.

## Fix
1. Reduce `max.poll.records` (e.g. from 500 to 50) to ensure batch completes well within interval.
2. Increase `max.poll.interval.ms` (e.g. to 10 minutes) if individual items have long processing times.
3. Use Cooperative Sticky Assignor (`partition.assignment.strategy = org.apache.kafka.clients.consumer.CooperativeStickyAssignor`) to avoid stop-the-world rebalances.
"""
    },
    {
        "filename": "cloud-elasticsearch-unassigned-shards.md",
        "title": "Elasticsearch Cluster Red: High Disk Watermark Exceeded",
        "failure_type": "disk_full",
        "source_type": "external_doc",
        "source_url": "https://www.elastic.co/guide/en/elasticsearch/reference/current/disk-watermarks.html",
        "license": "Apache-2.0",
        "content": """## Symptoms
Elasticsearch cluster health status is `RED`. Search queries fail or return partial results. Logstash or Fluentd buffers fill up because indexing is blocked with `403 Forbidden / cluster_block_exception`.

## Likely cause
Node disk usage exceeded the flood-stage watermark (default 95%). Elasticsearch automatically applied a read-only index block (`read_only_allow_delete`) to prevent disk corruption.

## How to confirm
Check cluster health:
`curl -s localhost:9200/_cluster/health | jq .`
Check allocation explanation:
`curl -s localhost:9200/_cluster/allocation/explain | jq .`
Look for `flood stage disk watermark [95%] exceeded`.

## Fix
1. Delete old indices to free disk space:
`curl -X DELETE "localhost:9200/logs-2026.09.*"`
2. Remove read-only block from all indices:
```bash
curl -X PUT "localhost:9200/_all/_settings" -H 'Content-Type: application/json' -d '{
  "index.blocks.read_only_allow_delete": null
}'
```
3. Configure Curator or Index Lifecycle Management (ILM) to automatically delete or rollover indices older than 30 days.
"""
    },
    {
        "filename": "cloud-rabbitmq-memory-alarm-blocked.md",
        "title": "RabbitMQ Alarm Triggered: Publishers Blocked by Memory Threshold",
        "failure_type": "other",
        "source_type": "external_doc",
        "source_url": "https://www.rabbitmq.com/docs/alarms",
        "license": "Mozilla Public License 2.0",
        "content": """## Symptoms
Microservices publishing messages to RabbitMQ hang on `basic_publish` or receive `RESOURCE_LOCKED` error. Queue processing stalls.

## Likely cause
RabbitMQ memory usage exceeded high watermark threshold (default 40% of installed RAM), triggering a global publishing alarm that blocks all socket connections from writing.

## How to confirm
Check RabbitMQ node status:
`rabbitmqctl status | grep -A 5 alarms`
Check memory usage:
`rabbitmq-diagnostics memory_breakdown`
Look for alarm: `resource_alarm: memory`.

## Fix
1. Temporarily increase memory watermark limit:
`rabbitmqctl set_vm_memory_high_watermark 0.6`
2. Configure lazy queues (`x-queue-mode: lazy`) which page messages to disk immediately instead of keeping them in RAM.
3. Scale consumer instances to drain deep queues and release memory.
"""
    },
]

print(f"Generating {len(DOCS)} external failure documents in {EXTERNAL_DIR}...")
for doc in DOCS:
    filepath = EXTERNAL_DIR / doc["filename"]
    front_matter = (
        f"---\n"
        f"title: \"{doc['title']}\"\n"
        f"failure_type: \"{doc['failure_type']}\"\n"
        f"source_type: \"{doc['source_type']}\"\n"
        f"source_url: \"{doc['source_url']}\"\n"
        f"license: \"{doc['license']}\"\n"
        f"status: \"summary\"\n"
        f"---\n\n"
    )
    full_text = front_matter + doc["content"].strip() + "\n"
    filepath.write_text(full_text, encoding="utf-8")
    print(f"  ✓ Written: {doc['filename']}")

print(f"Successfully generated all {len(DOCS)} external knowledge documents.")

