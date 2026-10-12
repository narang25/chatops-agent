# Runbook format

One Markdown file per failure in `data/runbooks/`, named `<failure_type>-<short-name>.md`.

```markdown
---
title: "OOMKilled: Diagnosis and Fix"
failure_type: out_of_memory
service: payment-service
severity: high
---

## Symptoms
## Likely cause
## How to confirm
## Fix
## Prevention
```

- `failure_type` must come from `failure_types.md`
- `service` is a service name, or `any` for generic runbooks
