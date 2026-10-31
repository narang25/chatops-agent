---
title: "Cloudflare Global Outage: ReDoS Regular Expression CPU Spike"
failure_type: "cpu_saturation"
source_type: "external_postmortem"
source_url: "https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/"
license: "CC BY 4.0"
status: "summary"
---

## Symptoms
All edge reverse proxy nodes reach 100% CPU utilization. HTTP 502 errors served to traffic globally. Core routing processes freeze.

## Likely cause
A newly deployed WAF rule contained a poorly written regular expression with catastrophic backtracking (e.g. `.*.*=.*`), which consumed exponential CPU cycles when evaluated against malformed input.

## How to confirm
Check CPU utilization across cluster: `top` or `mpstat -P ALL 1`.
Inspect CPU profile / flame graph:
`perf top` showing 99% CPU in `pcre_exec` or regex evaluation engine.
Correlate failure timestamp with recent WAF or route deployment.

## Fix
1. Immediately roll back the offending rule or disable the newly deployed WAF rule group.
2. Use non-backtracking regular expression engines (such as Google RE2 or Rust regex) which guarantee linear time evaluation $O(n)$.
3. Run automated regex static analysis in CI to detect exponential backtracking patterns prior to deployment.
