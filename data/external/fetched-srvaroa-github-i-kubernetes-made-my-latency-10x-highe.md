---
title: "Kubernetes made my latency 10x higher | Galo Navarro"
failure_type: network_timeout
source_type: external_postmortem
source_url: https://srvaroa.github.io/kubernetes/migration/latency/dns/java/aws/microservices/2019/10/22/kubernetes-added-a-0-to-my-latency.html
license: Public Postmortem Summary
status: external
---

## Summary
Kubernetes made my latency 10x higher

Update: it looks this post has gotten way more attention than I anticipated. I’ve seen / received feedback that the title is misleading and some people get dissapointed. I see why, so at the risk of spoiling the surprise, let me clarify what this is about before starting. As we migrate teams over to Kubernetes, I’m observing that every time someone has an issue, like “latency went up after migrating”, there is a knee-jerk reaction that “Kubernetes is to blame”, and investigations almost invariably result in “well, not really”. This post exemplifies one of these cases. The title is what our dev said, by the end you’ll see it wasn’t Kubernetes at all. There are no break through revelations to be learned about Kubernetes here, but I think there are good lessons about complex systems.

Last week my team was busy with the migration of one microservice to our central platform, which bundles CI/CD, a Kubernetes based runtime, metrics and other goodies. This exercise is meant to provide a blueprint to accelerate moving a fleet of ~150 more in the coming months, all of which power some of the main online marketplaces in Spain (Infojobs, Fotocasa, etc.)

After we had the application deployed in Kubernetes and routed some production traffic to it, things started looking worrisome. Request latencies in the Kubernetes deployment were up to x10 higher than on EC2. Unless we found a solution this would not only become a hard blocker to migrate this microservice, but could also jettison the entire project.

Why is latency so much higher in Kubernetes

## Reference
Full article / official documentation: https://srvaroa.github.io/kubernetes/migration/latency/dns/java/aws/microservices/2019/10/22/kubernetes-added-a-0-to-my-latency.html
