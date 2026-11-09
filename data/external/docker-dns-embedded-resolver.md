---
title: "Embedded DNS Resolver 127.0.0.11 Failure in Docker User Networks"
failure_type: "network_timeout"
source_type: "external_doc"
source_url: "https://docs.docker.com/network/drivers/bridge/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Containers on a custom user-defined bridge network fail to resolve other service names: `getaddrinfo ENOTFOUND order-service`. DNS requests to `127.0.0.11:53` time out.

## Likely cause
Docker internal DNS server thread within dockerd became hung or iptables routing rules for 127.0.0.11 were overwritten by host firewall (e.g. `ufw` reload or `firewalld`).

## How to confirm
From inside container:
`nslookup order-service 127.0.0.11`
Check iptables NAT table for Docker DNS PREROUTING rules:
`iptables -t nat -L DOCKER_OUTPUT -n`

## Fix
1. Verify containers share the exact same user-defined network: `docker network inspect <net_name>`.
2. Reload iptables and restart docker:
`systemctl restart docker`
3. Ensure host firewalld/ufw does not flush Docker chains.
