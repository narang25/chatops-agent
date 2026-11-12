---
title: "The shipwreck of GKE Cluster Upgrade // Deploy Live"
failure_type: bad_config
source_type: external_postmortem
source_url: https://deploy.live/blog/the-shipwreck-of-gke-cluster-upgrade/
license: Public Postmortem Summary
status: external
---

## Summary
The shipwreck of GKE Cluster Upgrade

I am a huge fan of the Google Cloud Platform and especially GKE. It was fundamental in our migration of Loveholidays on-prem applications to Kubernetes. GKE’s rich integrations with other GCP products allowed us to shift a lot of configuration from Ansible into Kubernetes yaml definitions which are now managed by GitOps. We are running GKE in Prod for 6+ months and will struggle to imagine any other way to run and deploy our applications now. The story I am about to tell you is a precaution on things that may go wrong during cluster/node upgrades. Its aim is to save you stress and worry next time you are in the same situation.

With the migration to GCP underway, we were too busy to focus on more BAU operations like cluster and node pools upgrades. We’ve got a little rusty and were two versions behind of what is available on GKE. 1.10.X vs 1.12.X. With the migration workload out of the way, we’ve finally got time to perform a long-overdue upgrade. Up to this point, we’ve tested same upgrades across multiple other clusters and environments. We’ve noticed that there were some changes that we had to keep in mind, but none of those changes had anything to do with a production application, cluster stability.

On the evening of the upgrade, I’ve estimated that 2-2.5 hours will be plenty to upgrade masters and NodePools. Cluster upgrade is a two-step process, first masters, then NodePools.

During the master node upgrade you are unable to change the cluster’s configuration for several minutes. I’ve chosen the latest available 1.12.5-gke.10 and

## Reference
Full article / official documentation: https://deploy.live/blog/the-shipwreck-of-gke-cluster-upgrade/
