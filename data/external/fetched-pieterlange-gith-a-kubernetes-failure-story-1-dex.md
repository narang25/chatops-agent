---
title: "A kubernetes failure story (#1 - dex)"
failure_type: bad_config
source_type: external_postmortem
source_url: https://pieterlange.github.io/failure-stories/2019-06.dex.html
license: Public Postmortem Summary
status: external
---

## Summary
Kinda need that to delete the resources

Delete namespace and let k8s clean up for us

Bypass k8s and delete resources in etcd

List all requests in order to delete

Can't access monitoring (no auth, no port-forward)

You cant actually remove that finalizer with kubectl

## Reference
Full article / official documentation: https://pieterlange.github.io/failure-stories/2019-06.dex.html
