---
title: "Kubernetes' dirty endpoint secret and Ingress · Phil Pearl's Blog"
failure_type: high_error_rate
source_type: external_postmortem
source_url: https://philpearl.github.io/post/k8s_ingress/
license: Public Postmortem Summary
status: external
---

## Summary
Kubernetes' dirty endpoint secret and Ingress

At Ravelin we’ve migrated to Kubernetes (on GKE). This has been very successful. We’ve got pod disruption budgets coming out of our ears, our statefulsets are very stately, and rolling node replacements run without a hitch.

The last piece of the puzzle is to move our API layer from the old VMs into our kubernetes cluster. For this we need to set up an Ingress so the API can be accessed from the outside world.

At first this seems straight-forward. We just define the ingress controller, tinker with terraform to get some IP addresses and Google takes care of nearly everything else. And it all works like magic. Great!

But we begin to notice our integration tests are occasionally receiving 502 errors. And there begins a journey that I’ll save you the pain of reading about by cutting directly to the final conclusions.

Everybody talks about Graceful shutdown. But you really shouldn’t do it in Kubernetes. Or at least not the Graceful shutdown you learned at your mother’s knee. This level of grace is unnecessary to the point of danger in the world of Kubernetes.

## Reference
Full article / official documentation: https://philpearl.github.io/post/k8s_ingress/
