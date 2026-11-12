---
title: "PostgreSQL: Documentation: 18: 20.1. The pg_hba.conf File"
failure_type: bad_config
source_type: external_doc
source_url: https://www.postgresql.org/docs/current/auth-pg-hba-conf.html
license: PostgreSQL License
status: external
---

## Summary
Client authentication is controlled by a configuration file, which traditionally is named pg_hba.conf and is stored in the database cluster's data directory. (HBA stands for host-based authentication.) A default pg_hba.conf file is installed when the data directory is initialized by initdb. It is possible to place the authentication configuration file elsewhere, however; see the hba_file configuration parameter.

The pg_hba.conf file is read on start-up and when the main server process receives a SIGHUP signal. If you edit the file on an active system, you will need to signal the postmaster (using pg_ctl reload, calling the SQL function pg_reload_conf(), or using kill -HUP) to make it re-read the file.

The preceding statement is not true on Microsoft Windows: there, any changes in the pg_hba.conf file are immediately applied by subsequent new connections.

The system view pg_hba_file_rules can be helpful for pre-testing changes to the pg_hba.conf file, or for diagnosing problems if loading of the file did not have the desired effects. Rows in the view with non-null error fields indicate problems in the corresponding lines of the file.

The general format of the pg_hba.conf file is a set of records, one per line. Blank lines are ignored, as is any text after the # comment character. A record can be continued onto the next line by ending the line with a backslash. (Backslashes are not special except at the end of a line.) A record is made up of a number of fields which are separated by spaces and/or tabs. Fields can contain white space if the field value is double-quoted. Qu

## Reference
Full article / official documentation: https://www.postgresql.org/docs/current/auth-pg-hba-conf.html
