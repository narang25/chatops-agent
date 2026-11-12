---
title: "PostgreSQL: Documentation: 18: Chapter 26. High Availability, Load Balancing, and Replication"
failure_type: other
source_type: external_doc
source_url: https://www.postgresql.org/docs/current/high-availability.html
license: PostgreSQL License
status: external
---

## Summary
Chapter 26. High Availability, Load Balancing, and Replication

Database servers can work together to allow a second server to take over quickly if the primary server fails (high availability), or to allow several computers to serve the same data (load balancing). Ideally, database servers could work together seamlessly. Web servers serving static web pages can be combined quite easily by merely load-balancing web requests to multiple machines. In fact, read-only database servers can be combined relatively easily too. Unfortunately, most database servers have a read/write mix of requests, and read/write servers are much harder to combine. This is because though read-only data needs to be placed on each server only once, a write to any server has to be propagated to all servers so that future read requests to those servers return consistent results.

This synchronization problem is the fundamental difficulty for servers working together. Because there is no single solution that eliminates the impact of the sync problem for all use cases, there are multiple solutions. Each solution addresses this problem in a different way, and minimizes its impact for a specific workload.

Some solutions deal with synchronization by allowing only one server to modify the data. Servers that can modify data are called read/write, master or primary servers. Servers that track changes in the primary are called standby or secondary servers. A standby server that cannot be connected to until it is promoted to a primary server is called a warm standby server, and one that can accept connections and

## Reference
Full article / official documentation: https://www.postgresql.org/docs/current/high-availability.html
