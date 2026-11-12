---
title: "Networking overview"
failure_type: network_timeout
source_type: external_doc
source_url: https://docs.docker.com/engine/network/
license: Apache-2.0
status: external
---

## Summary
Container networking refers to the ability for containers to connect to and communicate with each other, and with non-Docker network services.

Containers have networking enabled by default, and they can make outgoing connections. A container has no information about what kind of network it's attached to, or whether its network peers are also Docker containers. A container only sees a network interface with an IP address, a gateway, a routing table, DNS services, and other networking details.

This page describes networking from the point of view of the container, and the concepts around container networking.

When Docker Engine on Linux starts for the first time, it has a single built-in network called the "default bridge" network. When you run a container without the --network option, it is connected to the default bridge.

Containers attached to the default bridge have access to network services outside the Docker host. They use "masquerading" which means, if the Docker host has Internet access, no additional configuration is needed for the container to have Internet access.

For example, to run a container on the default bridge network, and have it ping an Internet host:

## Reference
Full article / official documentation: https://docs.docker.com/engine/network/
