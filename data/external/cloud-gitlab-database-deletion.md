---
title: "GitLab Production Outage: Accidental Directory Deletion in Disaster Recovery"
failure_type: "other"
source_type: "external_postmortem"
source_url: "https://about.gitlab.com/blog/2017/02/01/gitlab-dot-com-database-incident/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
Production database directory erased (`/var/opt/gitlab/postgresql/data`). Production database completely offline. Automated backups failed to restore.

## Likely cause
During stressful manual debugging of replication lag, an administrator ran `rm -rf` on the wrong terminal shell (primary server instead of replica). Five distinct backup mechanisms were either broken, untested, or expired.

## How to confirm
Check host data directory: `ls -la /var/opt/gitlab/postgresql/data` (directory empty).
Check database process status: `systemctl status postgresql`.

## Fix
1. Locate most recent valid snapshot (LVM snapshot or disk volume backup).
2. Restore snapshot to a separate staging host and replay write-ahead logs.
3. Automated disaster recovery drills: routinely verify backup restoration in automated CI pipelines.
4. Revoke direct interactive SSH shell root access to production primary databases; use audited automation.
