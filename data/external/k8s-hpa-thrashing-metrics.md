---
title: "Horizontal Pod Autoscaler Flapping: CPU Threshold Thrashing"
failure_type: "cpu_saturation"
source_type: "external_postmortem"
source_url: "https://k8s.af/hpa-flapping-scale-thrash"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
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
