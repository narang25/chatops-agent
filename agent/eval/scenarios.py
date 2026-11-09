"""
Benchmark scenarios for the ChatOps agent (Week 3 -- Task A11).

Each scenario contains:
  scenario_id          -- unique identifier
  service              -- service under test
  question             -- natural-language incident question sent to the agent
  failure_type         -- ground truth failure type (from contracts/failure_types.md)
  expected_fix_keywords -- keywords that must appear in the agent recommendation
  expected_runbook_keywords -- keywords that must appear in runbook citations
  ablation             -- which ablation mode: full | rag_only
"""

from __future__ import annotations

# All 10 failure types defined in contracts/failure_types.md are covered
BENCHMARK_SCENARIOS: list[dict] = [
    {
        "scenario_id": "oom-payment-001",
        "service": "payment-service",
        "question": "payment-service keeps restarting with memory errors. What is wrong?",
        "failure_type": "out_of_memory",
        "expected_fix_keywords": [
            "memory limit",
            "raise",
            "256",
            "leak"
        ],
        "expected_runbook_keywords": [
            "out_of_memory",
            "OOM",
            "memory"
        ],
        "ablation": "full"
    },
    {
        "scenario_id": "healthfail-inventory-001",
        "service": "inventory-service",
        "question": "inventory-service health check is returning 500. What is the root cause?",
        "failure_type": "health_check_failure",
        "expected_fix_keywords": [
            "health_fail",
            "false",
            "fault",
            "toggle",
            "admin"
        ],
        "expected_runbook_keywords": [
            "health_check_failure",
            "health",
            "500"
        ],
        "ablation": "full"
    },
    {
        "scenario_id": "badenv-order-001",
        "service": "order-service",
        "question": "order-service crashed at startup with a missing environment variable.",
        "failure_type": "bad_config",
        "expected_fix_keywords": [
            "env",
            "environment",
            "variable",
            "config",
            "DATABASE_URL"
        ],
        "expected_runbook_keywords": [
            "bad_config",
            "environment",
            "config"
        ],
        "ablation": "full"
    },
    {
        "scenario_id": "db-timeout-payment-001",
        "service": "payment-service",
        "question": "payment-service is timing out on database calls. Latency is very high.",
        "failure_type": "db_timeout",
        "expected_fix_keywords": [
            "connection pool",
            "timeout",
            "database",
            "retry"
        ],
        "expected_runbook_keywords": [
            "db_timeout",
            "timeout",
            "database"
        ],
        "ablation": "full"
    },
    {
        "scenario_id": "crash-loop-inventory-001",
        "service": "inventory-service",
        "question": "inventory-service is in a crash loop. Container restarts every 30 seconds.",
        "failure_type": "crash_loop",
        "expected_fix_keywords": [
            "restart",
            "exception",
            "dependency",
            "startup"
        ],
        "expected_runbook_keywords": [
            "crash_loop",
            "restart",
            "loop"
        ],
        "ablation": "full"
    },
    {
        "scenario_id": "cpu-saturation-any-001",
        "service": "payment-service",
        "question": "payment-service CPU is pegged at 100%. Response time has degraded.",
        "failure_type": "cpu_saturation",
        "expected_fix_keywords": [
            "cpu",
            "throttle",
            "limit",
            "scale",
            "thread"
        ],
        "expected_runbook_keywords": [
            "cpu_saturation",
            "cpu",
            "saturation"
        ],
        "ablation": "full"
    },
    {
        "scenario_id": "network-timeout-payment-001",
        "service": "payment-service",
        "question": "payment-service is getting network timeouts calling an upstream API.",
        "failure_type": "network_timeout",
        "expected_fix_keywords": [
            "network",
            "timeout",
            "upstream",
            "retry",
            "circuit"
        ],
        "expected_runbook_keywords": [
            "network_timeout",
            "network",
            "timeout"
        ],
        "ablation": "full"
    },
    {
        "scenario_id": "high-error-rate-order-001",
        "service": "order-service",
        "question": "order-service error rate spiked to 40%. Many 500s in logs.",
        "failure_type": "high_error_rate",
        "expected_fix_keywords": [
            "error_rate",
            "exception",
            "500",
            "rollback",
            "revert"
        ],
        "expected_runbook_keywords": [
            "high_error_rate",
            "error",
            "rate"
        ],
        "ablation": "full"
    },
    {
        "scenario_id": "disk-full-any-001",
        "service": "order-service",
        "question": "Services are failing with Errno 28 No space left on device.",
        "failure_type": "disk_full",
        "expected_fix_keywords": [
            "disk",
            "space",
            "prune",
            "docker",
            "logs",
            "volume"
        ],
        "expected_runbook_keywords": [
            "disk_full",
            "disk",
            "space",
            "Errno 28"
        ],
        "ablation": "full"
    },
    {
        "scenario_id": "dependency-failure-order-001",
        "service": "order-service",
        "question": "order-service is failing because an upstream dependency is down.",
        "failure_type": "dependency_failure",
        "expected_fix_keywords": [
            "dependency",
            "upstream",
            "circuit",
            "fallback",
            "retry"
        ],
        "expected_runbook_keywords": [
            "dependency_failure",
            "dependency",
            "upstream"
        ],
        "ablation": "full"
    }
]

# Surprise / unseen scenarios (Week 4 -- Task A18)
# These represent failures without a dedicated internal runbook.
# Correct answer is 'unknown' (or 'other') with useful evidence and safe next steps.
SURPRISE_SCENARIOS: list[dict] = [
    {
        "scenario_id": "surprise-db-auth-001",
        "service": "payment-service",
        "question": "payment-service cannot connect to PostgreSQL. Log reports: 'password authentication failed for user payment_user'.",
        "failure_type": "unknown",
        "acceptable_failure_types": ["unknown", "bad_config", "other"],
        "expected_fix_keywords": [
            "password",
            "credential",
            "secret",
            "auth",
            "environment"
        ],
        "expected_runbook_keywords": [],
        "ablation": "full"
    },
    {
        "scenario_id": "surprise-pool-exhaust-001",
        "service": "inventory-service",
        "question": "inventory-service database connection pool exhausted. Remaining connection slots are reserved for superuser.",
        "failure_type": "unknown",
        "acceptable_failure_types": ["unknown", "db_timeout", "other"],
        "expected_fix_keywords": [
            "connection",
            "pool",
            "slots",
            "max_connections",
            "idle"
        ],
        "expected_runbook_keywords": [],
        "ablation": "full"
    }
]
