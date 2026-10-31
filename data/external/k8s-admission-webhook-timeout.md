---
title: "Mutating/Validating Admission Webhook Timeout Blocks Deployments"
failure_type: "bad_config"
source_type: "external_postmortem"
source_url: "https://k8s.af/webhook-timeout-blocks-deployments"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
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
