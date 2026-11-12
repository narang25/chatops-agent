---
title: "Resource constraints"
failure_type: out_of_memory
source_type: external_doc
source_url: https://docs.docker.com/engine/containers/resource_constraints/
license: Apache-2.0
status: external
---

## Summary
By default, a container has no resource constraints and can use as much of a given resource as the host's kernel scheduler allows. Docker provides ways to control how much memory, or CPU a container can use, setting runtime configuration flags of the docker run command. This section provides details on when you should set such limits and the possible implications of setting them.

Many of these features require your kernel to support Linux capabilities. To check for support, you can use the docker info command. If a capability is disabled in your kernel, you may see a warning at the end of the output like the following:

Consult your operating system's documentation for enabling them. See also the Docker Engine troubleshooting guide for more information.

Understand the risks of running out of memory

It's important not to allow a running container to consume too much of the host machine's memory. On Linux hosts, if the kernel detects that there isn't enough memory to perform important system functions, it throws an OOME, or Out Of Memory Exception, and starts killing processes to free up memory. Any process is subject to killing, including Docker and other important applications. This can effectively bring the entire system down if the wrong process is killed.

Docker attempts to mitigate these risks by adjusting the OOM priority on the Docker daemon so that it's less likely to be killed than other processes on the system. The OOM priority on containers isn't adjusted. This makes it more likely for an individual container to be killed than for the Docker daemon or other sy

## Reference
Full article / official documentation: https://docs.docker.com/engine/containers/resource_constraints/
