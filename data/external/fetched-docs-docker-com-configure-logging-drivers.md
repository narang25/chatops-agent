---
title: "Configure logging drivers"
failure_type: bad_config
source_type: external_doc
source_url: https://docs.docker.com/engine/logging/configure/
license: Apache-2.0
status: external
---

## Summary
Docker includes multiple logging mechanisms to help you get information from running containers and services. These mechanisms are called logging drivers. Each Docker daemon has a default logging driver, which each container uses unless you configure it to use a different logging driver, or log driver for short.

As a default, Docker uses the json-file logging driver, which caches container logs as JSON internally. In addition to using the logging drivers included with Docker, you can also implement and use logging driver plugins.

Use the local logging driver to prevent disk-exhaustion. By default, no log-rotation is performed. As a result, log-files stored by the default json-file logging driver can cause a significant amount of disk space to be used for containers that generate much output, which can lead to disk space exhaustion.

Docker keeps the json-file logging driver (without log-rotation) as a default to remain backwards compatible with older versions of Docker, and for situations where Docker is used as runtime for Kubernetes.

For other situations, the local logging driver is recommended as it performs log-rotation by default, and uses a more efficient file format. Refer to the Configure the default logging driver section below to learn how to configure the local logging driver as a default, and the local file logging driver page for more details about the local logging driver.

Configure the default logging driver

## Reference
Full article / official documentation: https://docs.docker.com/engine/logging/configure/
