---
title: "Debugging Kubernetes nodes with crictl"
failure_type: other
source_type: external_doc
source_url: https://kubernetes.io/docs/tasks/debug/debug-cluster/crictl/
license: CC BY 4.0
status: external
---

## Summary
Debugging Kubernetes nodes with crictl

Debugging Kubernetes nodes with crictl

crictl is a command-line interface for CRI-compatible container runtimes. You can use it to inspect and debug container runtimes and applications on a Kubernetes node. crictl and its source are hosted in the cri-tools repository.

crictl requires a Linux operating system with a CRI runtime.

You can download a compressed archive crictl from the cri-tools release page, for several different architectures. Download the version that corresponds to your version of Kubernetes. Extract it and move it to a location on your system path, such as /usr/local/bin/.

The crictl command has several subcommands and runtime flags. Use crictl help or crictl <subcommand> help for more details.

## Reference
Full article / official documentation: https://kubernetes.io/docs/tasks/debug/debug-cluster/crictl/
