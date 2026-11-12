---
title: "Getting started"
failure_type: bad_config
source_type: external_doc
source_url: https://prometheus.io/docs/prometheus/latest/getting_started/
license: Apache-2.0
status: external
---

## Summary
This guide is a "Hello World"-style tutorial which shows how to install, configure, and use a simple Prometheus instance. You will download and run Prometheus locally, configure it to scrape itself and an example application, then work with queries, rules, and graphs to use collected time series data.

Download the latest release of Prometheus for your platform, then extract and run it:

Before starting Prometheus, let's configure it.

Configuring Prometheus to monitor itself

Prometheus collects metrics from targets by scraping metrics HTTP endpoints. Since Prometheus exposes data in the same manner about itself, it can also scrape and monitor its own health.

While a Prometheus server that collects only data about itself is not very useful, it is a good starting example. Save the following basic Prometheus configuration as a file named prometheus.yml:

## Reference
Full article / official documentation: https://prometheus.io/docs/prometheus/latest/getting_started/
