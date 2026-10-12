# Incident ground truth

Every captured failure in `data/incident_logs/` has two files:
`<scenario_id>.jsonl` (logs, see logs.md) and `<scenario_id>.meta.json`:

```json
{
  "scenario_id": "oom-payment-001",
  "service": "payment-service",
  "failure_type": "out_of_memory",
  "root_cause": "Memory limit (64MB) too low; /leak allocates unbounded memory",
  "expected_fix": "Raise memory limit to 256MB and fix the leak",
  "signals": ["oom_killed=true", "exit_code=137", "restart_count increasing"],
  "how_to_reproduce": "python infra/failures/oom.py"
}
```

Used by Person A to write matching runbooks and by the Week 4 benchmark to score the agent.
