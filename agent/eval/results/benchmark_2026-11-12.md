# ChatOps Agent Benchmark Report — `benchmark_2026-11-12`

- **Timestamp**: 2026-11-12 13:51:19 UTC
- **Ablations Evaluated**: `llm_only`, `full`
- **Models**: `default`
- **Hold-Out Setting**: `None`
- **Total Evaluations**: `48`

## Summary Results

| Configuration | Model | FT Accuracy | Fix Quality | Citation Rate | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `llm_only` | `default` | **20.8%** | 49.4% | 0.0% | 0.0 | 10.91s | $0.0016 |
| `full` | `default` | **66.7%** | 80.6% | 100.0% | 12.25 | 20.46s | $0.0129 |

## Evaluation Details

| Scenario | Ablation | Model | Trial | FT Match | Fix Score | RB Cited | Tools | Latency |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `baddeploy-order-001` | `llm_only` | `default` | 1 | ❌ | 0.40 | ❌ | 0 | 16.4s |
| `badenv-order-001` | `llm_only` | `default` | 1 | ❌ | 0.25 | ❌ | 0 | 10.4s |
| `cpusat-payment-001` | `llm_only` | `default` | 1 | ❌ | 0.25 | ❌ | 0 | 8.2s |
| `crashloop-payment-001` | `llm_only` | `default` | 1 | ❌ | 1.00 | ❌ | 0 | 10.1s |
| `dbtimeout-payment-001` | `llm_only` | `default` | 1 | ❌ | 0.40 | ❌ | 0 | 12.0s |
| `depfail-order-001` | `llm_only` | `default` | 1 | ❌ | 0.80 | ❌ | 0 | 10.4s |
| `diskfull-inventory-001` | `llm_only` | `default` | 1 | ✅ | 0.50 | ❌ | 0 | 16.1s |
| `healthfail-inventory-001` | `llm_only` | `default` | 1 | ❌ | 0.40 | ❌ | 0 | 11.5s |
| `nettimeout-order-001` | `llm_only` | `default` | 1 | ❌ | 0.60 | ❌ | 0 | 7.7s |
| `oom-payment-001` | `llm_only` | `default` | 1 | ❌ | 0.25 | ❌ | 0 | 9.2s |
| `surprise_1` | `llm_only` | `default` | 1 | ❌ | 0.40 | ❌ | 0 | 10.4s |
| `surprise_2` | `llm_only` | `default` | 1 | ✅ | 0.40 | ❌ | 0 | 15.6s |
| `baddeploy-order-001` | `llm_only` | `default` | 2 | ❌ | 0.20 | ❌ | 0 | 11.1s |
| `badenv-order-001` | `llm_only` | `default` | 2 | ❌ | 0.75 | ❌ | 0 | 10.0s |
| `cpusat-payment-001` | `llm_only` | `default` | 2 | ❌ | 0.50 | ❌ | 0 | 9.7s |
| `crashloop-payment-001` | `llm_only` | `default` | 2 | ✅ | 1.00 | ❌ | 0 | 12.6s |
| `dbtimeout-payment-001` | `llm_only` | `default` | 2 | ✅ | 0.60 | ❌ | 0 | 11.1s |
| `depfail-order-001` | `llm_only` | `default` | 2 | ❌ | 0.60 | ❌ | 0 | 11.3s |
| `diskfull-inventory-001` | `llm_only` | `default` | 2 | ✅ | 0.50 | ❌ | 0 | 12.9s |
| `healthfail-inventory-001` | `llm_only` | `default` | 2 | ❌ | 0.40 | ❌ | 0 | 10.6s |
| `nettimeout-order-001` | `llm_only` | `default` | 2 | ❌ | 0.60 | ❌ | 0 | 6.3s |
| `oom-payment-001` | `llm_only` | `default` | 2 | ❌ | 0.25 | ❌ | 0 | 10.0s |
| `surprise_1` | `llm_only` | `default` | 2 | ❌ | 0.40 | ❌ | 0 | 9.1s |
| `surprise_2` | `llm_only` | `default` | 2 | ❌ | 0.40 | ❌ | 0 | 9.3s |
| `baddeploy-order-001` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 11 | 26.5s |
| `badenv-order-001` | `full` | `default` | 1 | ✅ | 0.75 | ✅ | 10 | 18.7s |
| `cpusat-payment-001` | `full` | `default` | 1 | ✅ | 0.75 | ✅ | 12 | 22.5s |
| `crashloop-payment-001` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 10 | 18.5s |
| `dbtimeout-payment-001` | `full` | `default` | 1 | ❌ | 0.80 | ✅ | 12 | 16.2s |
| `depfail-order-001` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 16 | 25.7s |
| `diskfull-inventory-001` | `full` | `default` | 1 | ✅ | 0.75 | ✅ | 11 | 18.2s |
| `healthfail-inventory-001` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 10 | 18.3s |
| `nettimeout-order-001` | `full` | `default` | 1 | ❌ | 0.60 | ✅ | 16 | 20.7s |
| `oom-payment-001` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 11 | 17.3s |
| `surprise_1` | `full` | `default` | 1 | ❌ | 0.80 | ✅ | 11 | 15.2s |
| `surprise_2` | `full` | `default` | 1 | ❌ | 0.20 | ✅ | 14 | 22.2s |
| `baddeploy-order-001` | `full` | `default` | 2 | ✅ | 0.80 | ✅ | 10 | 13.4s |
| `badenv-order-001` | `full` | `default` | 2 | ✅ | 1.00 | ✅ | 10 | 16.7s |
| `cpusat-payment-001` | `full` | `default` | 2 | ❌ | 0.75 | ✅ | 13 | 21.3s |
| `crashloop-payment-001` | `full` | `default` | 2 | ✅ | 1.00 | ✅ | 10 | 17.6s |
| `dbtimeout-payment-001` | `full` | `default` | 2 | ❌ | 0.80 | ✅ | 12 | 17.6s |
| `depfail-order-001` | `full` | `default` | 2 | ✅ | 0.80 | ✅ | 16 | 36.9s |
| `diskfull-inventory-001` | `full` | `default` | 2 | ✅ | 0.75 | ✅ | 11 | 19.4s |
| `healthfail-inventory-001` | `full` | `default` | 2 | ✅ | 1.00 | ✅ | 11 | 19.8s |
| `nettimeout-order-001` | `full` | `default` | 2 | ❌ | 0.60 | ✅ | 16 | 21.2s |
| `oom-payment-001` | `full` | `default` | 2 | ✅ | 1.00 | ✅ | 11 | 18.1s |
| `surprise_1` | `full` | `default` | 2 | ✅ | 1.00 | ✅ | 12 | 19.8s |
| `surprise_2` | `full` | `default` | 2 | ❌ | 0.60 | ✅ | 18 | 29.1s |

---
_Generated automatically by ChatOps Benchmark Harness v2_