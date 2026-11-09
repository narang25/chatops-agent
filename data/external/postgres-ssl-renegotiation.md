---
title: "SSL Connection Renegotiation Failure Under High Concurrency"
failure_type: "network_timeout"
source_type: "external_doc"
source_url: "https://www.postgresql.org/docs/current/ssl-tcp.html"
license: "PostgreSQL License"
status: "summary"
---

## Symptoms
Microservices connecting over TLS/SSL experience sudden connection drops with `SSL error: decryption failed or bad record mac` or handshake timeouts.

## Likely cause
SSL renegotiation limit reached in older Postgres setups or OpenSSL library compatibility conflict between client container and server.

## How to confirm
Check Postgres log for SSL messages:
`grep -i "ssl" /var/log/postgresql/postgresql.log`
Test connection with openssl s_client:
`openssl s_client -connect postgres.internal:5432 -starttls postgres`

## Fix
1. Ensure `ssl_renegotiation_limit = 0` in `postgresql.conf` (disables periodic renegotiation).
2. Align TLS cipher suites: `ssl_ciphers = 'HIGH:!aNULL'`.
3. Update client database driver in microservice container to use TLS 1.3.
