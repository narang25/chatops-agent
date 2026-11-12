---
title: "Defining recording rules"
failure_type: bad_config
source_type: external_doc
source_url: https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/
license: Apache-2.0
status: external
---

## Summary
Prometheus supports two types of rules which may be configured and then evaluated at regular intervals: recording rules and alerting rules. To include rules in Prometheus, create a file containing the necessary rule statements and have Prometheus load the file via the rule_files field in the Prometheus configuration. Rule files use YAML.

The rule files can be reloaded at runtime by sending SIGHUP to the Prometheus process. The changes are only applied if all rule files are well-formatted.

To quickly check whether a rule file is syntactically correct without starting a Prometheus server, you can use Prometheus's promtool command-line utility tool:

The promtool binary is part of the prometheus archive offered on the project's download page.

When the file is syntactically valid, the checker prints a textual representation of the parsed rules to standard output and then exits with a 0 return status.

If there are any syntax errors or invalid input arguments, it prints an error message to standard error and exits with a 1 return status.

## Reference
Full article / official documentation: https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/
