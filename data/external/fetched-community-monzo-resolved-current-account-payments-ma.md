---
title: "RESOLVED: Current account payments may fail - Major Outage (27/10/2017) - #95 by anon77247897 - Help - Monzo Community"
failure_type: other
source_type: external_postmortem
source_url: https://community.monzo.com/t/resolved-current-account-payments-may-fail-major-outage-27-10-2017/26296/95
license: Public Postmortem Summary
status: external
---

## Summary
RESOLVED: Current account payments may fail - Major Outage (27/10/2017)

Hi everyone I’m Monzo’s Head of Engineering, and as I promised on Friday I’d like to share some more information about what happened during this outage. Because the nature of the issue was technical, this post is also quite technical.

It’s important to note that we had two major incidents last week that many of you will have experienced (sorry again.) The first incident lasted most of the week and affected only our prepaid product – ie. Monzo Alpha and Beta cards. The second outage affected both the prepaid product and our new current account for a period of around 1½ hours on Friday afternoon. This post is about the latter.

You can learn more about our overall backend architecture in this blog post I published last year, but it’s important to understand the role of a few components in our stack at a high level to understand this issue:

Kubernetes is a system which deploys and manages all of our infrastructure. Monzo’s backend is written as several hundred microservices, packaged into Docker containers. Kubernetes manages these Docker containers and ensures they are running properly across our fleet of AWS nodes.

etcd is a distributed database used by Kubernetes to store information about which services are deployed, where they are running, and what state they’re in. Kubernetes requires a stable connection to etcd in order to work properly, although if etcd does go down all of our services do continue running – they just can’t be upgraded, or scaled up or down.

## Reference
Full article / official documentation: https://community.monzo.com/t/resolved-current-account-payments-may-fail-major-outage-27-10-2017/26296/95
