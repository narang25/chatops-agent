# ChatOps Agent Benchmark Report — `benchmark_2026-11-12`

- **Timestamp**: 2026-11-12 10:12:16 UTC
- **Ablations Evaluated**: `llm_only`, `full`
- **Models**: `default`
- **Hold-Out Setting**: `None`
- **Total Evaluations**: `48`

## Summary Results

| Configuration | Model | FT Accuracy | Fix Quality | Citation Rate | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `llm_only` | `default` | **20.8%** | 49.4% | 79.2% | 0.0 | 10.91s | $0.0016 |
| `full` | `default` | **62.5%** | 69.4% | 83.3% | 12.88 | 20.24s | $0.0133 |

## Evaluation Details

| Scenario | Ablation | Model | Trial | FT Match | Fix Score | RB Cited | Tools | Latency |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `baddeploy-order-001` | `llm_only` | `default` | 1 | ❌ | 0.40 | ✅ | 0 | 16.4s |
| `badenv-order-001` | `llm_only` | `default` | 1 | ❌ | 0.25 | ✅ | 0 | 10.4s |
| `cpusat-payment-001` | `llm_only` | `default` | 1 | ❌ | 0.25 | ❌ | 0 | 8.2s |
| `crashloop-payment-001` | `llm_only` | `default` | 1 | ❌ | 1.00 | ✅ | 0 | 10.1s |
| `dbtimeout-payment-001` | `llm_only` | `default` | 1 | ❌ | 0.40 | ✅ | 0 | 12.0s |
| `depfail-order-001` | `llm_only` | `default` | 1 | ❌ | 0.80 | ✅ | 0 | 10.4s |
| `diskfull-inventory-001` | `llm_only` | `default` | 1 | ✅ | 0.50 | ✅ | 0 | 16.1s |
| `healthfail-inventory-001` | `llm_only` | `default` | 1 | ❌ | 0.40 | ✅ | 0 | 11.5s |
| `nettimeout-order-001` | `llm_only` | `default` | 1 | ❌ | 0.60 | ✅ | 0 | 7.7s |
| `oom-payment-001` | `llm_only` | `default` | 1 | ❌ | 0.25 | ✅ | 0 | 9.2s |
| `surprise_1` | `llm_only` | `default` | 1 | ❌ | 0.40 | ❌ | 0 | 10.4s |
| `surprise_2` | `llm_only` | `default` | 1 | ✅ | 0.40 | ❌ | 0 | 15.6s |
| `baddeploy-order-001` | `llm_only` | `default` | 2 | ❌ | 0.20 | ✅ | 0 | 11.1s |
| `badenv-order-001` | `llm_only` | `default` | 2 | ❌ | 0.75 | ✅ | 0 | 10.0s |
| `cpusat-payment-001` | `llm_only` | `default` | 2 | ❌ | 0.50 | ✅ | 0 | 9.7s |
| `crashloop-payment-001` | `llm_only` | `default` | 2 | ✅ | 1.00 | ✅ | 0 | 12.6s |
| `dbtimeout-payment-001` | `llm_only` | `default` | 2 | ✅ | 0.60 | ✅ | 0 | 11.1s |
| `depfail-order-001` | `llm_only` | `default` | 2 | ❌ | 0.60 | ✅ | 0 | 11.3s |
| `diskfull-inventory-001` | `llm_only` | `default` | 2 | ✅ | 0.50 | ✅ | 0 | 12.9s |
| `healthfail-inventory-001` | `llm_only` | `default` | 2 | ❌ | 0.40 | ✅ | 0 | 10.6s |
| `nettimeout-order-001` | `llm_only` | `default` | 2 | ❌ | 0.60 | ✅ | 0 | 6.3s |
| `oom-payment-001` | `llm_only` | `default` | 2 | ❌ | 0.25 | ✅ | 0 | 10.0s |
| `surprise_1` | `llm_only` | `default` | 2 | ❌ | 0.40 | ❌ | 0 | 9.1s |
| `surprise_2` | `llm_only` | `default` | 2 | ❌ | 0.40 | ❌ | 0 | 9.3s |
| `baddeploy-order-001` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 11 | 38.0s |
| `badenv-order-001` | `full` | `default` | 1 | ✅ | 0.75 | ✅ | 10 | 17.5s |
| `cpusat-payment-001` | `full` | `default` | 1 | ❌ | 0.50 | ✅ | 10 | 17.2s |
| `crashloop-payment-001` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 10 | 16.6s |
| `dbtimeout-payment-001` | `full` | `default` | 1 | ❌ | 0.60 | ✅ | 13 | 19.4s |
| `depfail-order-001` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 20 | 31.5s |
| `diskfull-inventory-001` | `full` | `default` | 1 | ✅ | 0.75 | ✅ | 11 | 20.1s |
| `healthfail-inventory-001` | `full` | `default` | 1 | ✅ | 0.60 | ✅ | 11 | 19.5s |
| `nettimeout-order-001` | `full` | `default` | 1 | ❌ | 0.80 | ✅ | 18 | 23.2s |
| `oom-payment-001` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 11 | 18.6s |
| `surprise_1` | `full` | `default` | 1 | ✅ | 0.80 | ❌ | 12 | 19.9s |
| `surprise_2` | `full` | `default` | 1 | ❌ | 0.00 | ❌ | 15 | 21.7s |
| `baddeploy-order-001` | `full` | `default` | 2 | ✅ | 0.80 | ✅ | 11 | 17.5s |
| `badenv-order-001` | `full` | `default` | 2 | ✅ | 0.75 | ✅ | 11 | 18.3s |
| `cpusat-payment-001` | `full` | `default` | 2 | ❌ | 0.75 | ✅ | 12 | 16.6s |
| `crashloop-payment-001` | `full` | `default` | 2 | ✅ | 1.00 | ✅ | 10 | 16.7s |
| `dbtimeout-payment-001` | `full` | `default` | 2 | ❌ | 0.60 | ✅ | 13 | 18.3s |
| `depfail-order-001` | `full` | `default` | 2 | ✅ | 0.80 | ✅ | 11 | 15.7s |
| `diskfull-inventory-001` | `full` | `default` | 2 | ✅ | 0.75 | ✅ | 11 | 18.9s |
| `healthfail-inventory-001` | `full` | `default` | 2 | ✅ | 0.40 | ✅ | 11 | 14.1s |
| `nettimeout-order-001` | `full` | `default` | 2 | ❌ | 0.60 | ✅ | 30 | 28.1s |
| `oom-payment-001` | `full` | `default` | 2 | ✅ | 1.00 | ✅ | 12 | 19.4s |
| `surprise_1` | `full` | `default` | 2 | ❌ | 0.80 | ❌ | 11 | 17.4s |
| `surprise_2` | `full` | `default` | 2 | ❌ | 0.00 | ❌ | 14 | 21.5s |

---
_Generated automatically by ChatOps Benchmark Harness v2_