---
title: "Troubleshooting Clusters"
failure_type: other
source_type: external_doc
source_url: https://kubernetes.io/docs/tasks/debug/debug-cluster/
license: CC BY 4.0
status: external
---

## Summary
This doc is about cluster troubleshooting; we assume you have already ruled out your application as the root cause of the problem you are experiencing. See the application troubleshooting guide for tips on application debugging. You may also visit the troubleshooting overview document for more information.

For troubleshooting kubectl, refer to Troubleshooting kubectl.

The first thing to debug in your cluster is if your nodes are all registered correctly.

And verify that all of the nodes you expect to see are present and that they are all in the Ready state.

To get detailed information about the overall health of your cluster, you can run:

Example: debugging a down/unreachable node

## Reference
Full article / official documentation: https://kubernetes.io/docs/tasks/debug/debug-cluster/
