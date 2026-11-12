---
title: "PostgreSQL: Documentation: 18: 27.2. The Cumulative Statistics System"
failure_type: bad_config
source_type: external_doc
source_url: https://www.postgresql.org/docs/current/monitoring-stats.html
license: PostgreSQL License
status: external
---

## Summary
27.2. The Cumulative Statistics System #

PostgreSQL's cumulative statistics system supports collection and reporting of information about server activity. Presently, accesses to tables and indexes in both disk-block and individual-row terms are counted. The total number of rows in each table, and information about vacuum and analyze actions for each table are also counted. If enabled, calls to user-defined functions and the total time spent in each one are counted as well.

PostgreSQL also supports reporting dynamic information about exactly what is going on in the system right now, such as the exact command currently being executed by other server processes, and which other connections exist in the system. This facility is independent of the cumulative statistics system.

27.2.1. Statistics Collection Configuration #

Since collection of statistics adds some overhead to query execution, the system can be configured to collect or not collect information. This is controlled by configuration parameters that are normally set in postgresql.conf. (See Chapter 19 for details about setting configuration parameters.)

The parameter track_activities enables monitoring of the current command being executed by any server process.

## Reference
Full article / official documentation: https://www.postgresql.org/docs/current/monitoring-stats.html
