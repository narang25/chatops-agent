---
title: "Maximize learnings from a Kubernetes cluster failure · TBNL"
failure_type: other
source_type: external_postmortem
source_url: https://www.tibobeijen.nl/2019/02/01/learning-from-kubernetes-cluster-failure/
license: Public Postmortem Summary
status: external
---

## Summary
…another view on the web and how it’s built

Maximize learnings from a Kubernetes cluster failure

Since a number of months we (NU.nl development team) operate a small number of Kubernetes clusters. We see the potential of Kubernetes and how it can increase our productivity and how it can improve our CI/CD practices. Currently we run part of our logging and building toolset on Kubernetes, plus some small (internal) customer facing workloads, with the plan to move more applications there once we have build up knowledge and confidence.

Recently our team faced some problems on one of the clusters. Not as severe as to bring down the cluster completely, but definitely affecting the user experience of some internally used tools and dashboards.

Coincidentally, around the same time I visited DevOpsCon 2018 in Munich, where the opening keynote “Staying Alive: Patterns for Failure Management from the Bottom of the Ocean” related very well to this incident.

The talk (by Ronnie Chen, engineering manager at Twitter) focussed on various ways to make DevOps teams more effective in preventing and handling failures. One of the topics addressed was how catastrophes are usually caused by a cascade of failures, resulting in this quote:

## Reference
Full article / official documentation: https://www.tibobeijen.nl/2019/02/01/learning-from-kubernetes-cluster-failure/
