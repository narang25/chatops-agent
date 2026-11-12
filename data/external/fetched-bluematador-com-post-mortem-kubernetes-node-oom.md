---
title: "Post Mortem: Kubernetes Node OOM"
failure_type: out_of_memory
source_type: external_postmortem
source_url: https://www.bluematador.com/blog/post-mortem-kubernetes-node-oom
license: Public Postmortem Summary
status: external
---

## Summary
Production issues are never fun. They always seem to happen when you’re not at work, and the cause always seems to be silly. We recently had issues in our production Kubernetes cluster with nodes running out of memory, but the node recovered very quickly without any noticeable interruptions. In this blog we will go over the specific issue that happened in our cluster, what the impact was, and how we will avoid this issue in the future.

Blue Matador (yes we monitor ourselves!) creates an alert saying that one of the Kubernetes nodes in our production cluster had a SystemOOM event

Blue Matador creates a warning saying that EBS Burst Balance is low on the root volume for node that had a SystemOOM event. While the Burst Balance event came in after the SystemOOM event, the actual CloudWatch data shows that burst balance was at its lowest point at 5:02pm. The delay is due to the fact that EBS metrics are consistently 10-15 minutes behind, so our system cannot catch everything in real-time.

This is when I actually notice the alert and warning. I do a quick kubectl get pods to see what the impact is, and am surprised to see that zero of our application pods died. Using kubectl top nodes also does not show that the node in question is having memory issues -- it had already recovered, and memory usage was at ~60%. It’s just after 5 o’clock, and I did not want my Session IPA to get warm. After confirming that the node was healthy, and no pods were impacted, I assumed there must have been a fluke. Definitely something I can investigate on Monday.

Here’s the entire Slack conversatio

## Reference
Full article / official documentation: https://www.bluematador.com/blog/post-mortem-kubernetes-node-oom
