# ChatOps Agent Benchmark Report — `benchmark_variants_2026-11-12`

- **Timestamp**: 2026-11-13 17:18:05 UTC
- **Ablations Evaluated**: `full`
- **Models**: `default`
- **Hold-Out Setting**: `None`
- **Total Evaluations**: `20`

## Summary Results

| Configuration | Model | FT Accuracy | Fix Quality | Citation Rate | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `full` | `default` | **55.0%** | 74.8% | 75.0% | 11.6 | 23.35s | $0.0128 |

## Evaluation Details

| Scenario | Ablation | Model | Trial | FT Match | Fix Score | RB Cited | Tools | Latency |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `healthfail-payment-v1` | `full` | `default` | 1 | ❌ | 0.80 | ✅ | 11 | 28.1s |
| `healthfail-order-v1` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 10 | 19.2s |
| `healthfail-inventory-v1` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 11 | 17.6s |
| `dbtimeout-payment-v1` | `full` | `default` | 1 | ❌ | 0.40 | ❌ | 12 | 20.3s |
| `dbtimeout-order-v1` | `full` | `default` | 1 | ❌ | 0.20 | ❌ | 12 | 20.8s |
| `dbtimeout-inventory-v1` | `full` | `default` | 1 | ❌ | 0.20 | ❌ | 14 | 20.1s |
| `dberror-payment-v1` | `full` | `default` | 1 | ❌ | 0.60 | ✅ | 11 | 17.0s |
| `dberror-order-v1` | `full` | `default` | 1 | ❌ | 0.80 | ✅ | 11 | 19.2s |
| `dberror-inventory-v1` | `full` | `default` | 1 | ❌ | 0.80 | ❌ | 11 | 15.2s |
| `oom-payment-48m` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 11 | 18.7s |
| `oom-payment-64m` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 11 | 21.1s |
| `oom-payment-128m` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 11 | 45.8s |
| `baddeploy-order-er20` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 13 | 30.3s |
| `baddeploy-order-er50` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 11 | 26.9s |
| `baddeploy-order-er85` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 11 | 23.1s |
| `cpusat-payment-500ms` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 12 | 23.2s |
| `cpusat-payment-1500ms` | `full` | `default` | 1 | ✅ | 0.75 | ✅ | 12 | 24.7s |
| `nettimeout-order-1000ms` | `full` | `default` | 1 | ✅ | 0.80 | ✅ | 13 | 20.6s |
| `nettimeout-order-2500ms` | `full` | `default` | 1 | ❌ | 0.80 | ✅ | 12 | 25.6s |
| `nettimeout-order-5000ms` | `full` | `default` | 1 | ❌ | 0.80 | ❌ | 12 | 29.6s |

---
_Generated automatically by ChatOps Benchmark Harness v2_