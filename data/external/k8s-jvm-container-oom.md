---
title: "Silent JVM Process Kill: -Xmx Exceeds Kubernetes Memory Limit"
failure_type: "out_of_memory"
source_type: "external_postmortem"
source_url: "https://k8s.af/jvm-cgroups-memory-limit-oom"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
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
