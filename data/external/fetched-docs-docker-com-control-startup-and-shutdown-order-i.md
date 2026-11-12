---
title: "Control startup and shutdown order in Compose"
failure_type: network_timeout
source_type: external_doc
source_url: https://docs.docker.com/compose/how-tos/startup-order/
license: Apache-2.0
status: external
---

## Summary
Control startup and shutdown order in Compose

You can control the order of service startup and shutdown with the depends_on attribute. Compose always starts and stops containers in dependency order, where dependencies are determined by depends_on, links, volumes_from, and network_mode: "service:...".

For example, if your application needs to access a database and both services are started with docker compose up, there is a chance this will fail since the application service might start before the database service and won't find a database able to handle its SQL statements.

On startup, Compose does not wait until a container is "ready", only until it's running. This can cause issues if, for example, you have a relational database system that needs to start its own services before being able to handle incoming connections.

The solution for detecting the ready state of a service is to use the condition attribute with one of the following options:

service_healthy. This specifies that a dependency is expected to be “healthy”, which is defined with healthcheck, before starting a dependent service.

## Reference
Full article / official documentation: https://docs.docker.com/compose/how-tos/startup-order/
