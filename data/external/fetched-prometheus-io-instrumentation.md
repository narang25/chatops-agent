---
title: "Instrumentation"
failure_type: network_timeout
source_type: external_doc
source_url: https://prometheus.io/docs/practices/instrumentation/
license: Apache-2.0
status: external
---

## Summary
This page provides an opinionated set of guidelines for instrumenting your code.

The short answer is to instrument everything. Every library, subsystem and service should have at least a few metrics to give you a rough idea of how it is performing.

Instrumentation should be an integral part of your code. Instantiate the metric classes in the same file you use them. This makes going from alert to console to code easy when you are chasing an error.

For monitoring purposes, services can generally be broken down into three types: online-serving, offline-processing, and batch jobs. There is overlap between them, but every service tends to fit well into one of these categories.

An online-serving system is one where a human or another system is expecting an immediate response. For example, most database and HTTP requests fall into this category.

The key metrics in such a system are the number of performed queries, errors, and latency. The number of in-progress requests can also be useful.

## Reference
Full article / official documentation: https://prometheus.io/docs/practices/instrumentation/
