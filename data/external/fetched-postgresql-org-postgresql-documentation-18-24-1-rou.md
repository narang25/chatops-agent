---
title: "PostgreSQL: Documentation: 18: 24.1. Routine Vacuuming"
failure_type: other
source_type: external_doc
source_url: https://www.postgresql.org/docs/current/routine-vacuuming.html
license: PostgreSQL License
status: external
---

## Summary
PostgreSQL databases require periodic maintenance known as vacuuming. For many installations, it is sufficient to let vacuuming be performed by the autovacuum daemon, which is described in Section 24.1.6. You might need to adjust the autovacuuming parameters described there to obtain best results for your situation. Some database administrators will want to supplement or replace the daemon's activities with manually-managed VACUUM commands, which typically are executed according to a schedule by cron or Task Scheduler scripts. To set up manually-managed vacuuming properly, it is essential to understand the issues discussed in the next few subsections. Administrators who rely on autovacuuming may still wish to skim this material to help them understand and adjust autovacuuming.

PostgreSQL's VACUUM command has to process each table on a regular basis for several reasons:

To recover or reuse disk space occupied by updated or deleted rows.

To update data statistics used by the PostgreSQL query planner.

To update the visibility map, which speeds up index-only scans.

To protect against loss of very old data due to transaction ID wraparound or multixact ID wraparound.

## Reference
Full article / official documentation: https://www.postgresql.org/docs/current/routine-vacuuming.html
