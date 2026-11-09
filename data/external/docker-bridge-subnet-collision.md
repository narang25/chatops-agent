---
title: "Docker Network Routing Blackhole: Bridge IP Overlaps Host Subnet"
failure_type: "dependency_failure"
source_type: "external_doc"
source_url: "https://docs.docker.com/network/packet-filtering-firewalls/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Containers cannot connect to company intranet, external DB, or corporate LDAP (`no route to host` or packet drop). Host can reach the destination fine, but containers cannot.

## Likely cause
Docker default bridge network `docker0` auto-allocated subnet `172.17.0.0/16` or `172.18.0.0/16` which collides with the organization's physical VPC/LAN network range.

## How to confirm
Check host routing table: `ip route` or `netstat -rn`.
Inspect Docker bridge subnet:
`docker network inspect bridge | grep -i subnet`
Compare container subnet with company VPN/VPC IP range.

## Fix
1. Configure custom pool in `/etc/docker/daemon.json`:
```json
{
  "default-address-pools": [
    {"base": "10.200.0.0/16", "size": 24}
  ]
}
```
2. Restart docker service: `systemctl restart docker`.
3. Recreate affected docker networks: `docker network rm <net> && docker compose up -d`.
