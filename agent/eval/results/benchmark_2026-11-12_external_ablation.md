# ChatOps Agent Benchmark Report — `benchmark_2026-11-12`

- **Timestamp**: 2026-11-12 12:22:19 UTC
- **Ablations Evaluated**: `full`, `with_external`
- **Models**: `default`
- **Hold-Out Setting**: `None`
- **Total Evaluations**: `6`

## Summary Results

| Configuration | Model | FT Accuracy | Fix Quality | Citation Rate | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `full` | `default` | **66.7%** | 60.0% | 33.3% | 13.0 | 21.42s | $0.0136 |
| `with_external` | `default` | **66.7%** | 73.3% | 33.3% | 13.33 | 23.45s | $0.0142 |

## Evaluation Details

| Scenario | Ablation | Model | Trial | FT Match | Fix Score | RB Cited | Tools | Latency |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `oom-payment-001` | `full` | `default` | 1 | ✅ | 1.00 | ✅ | 13 | 26.9s |
| `surprise_1` | `full` | `default` | 1 | ✅ | 0.80 | ❌ | 12 | 15.8s |
| `surprise_2` | `full` | `default` | 1 | ❌ | 0.00 | ❌ | 14 | 21.5s |
| `oom-payment-001` | `with_external` | `default` | 1 | ✅ | 1.00 | ✅ | 11 | 29.5s |
| `surprise_1` | `with_external` | `default` | 1 | ✅ | 0.80 | ❌ | 12 | 18.2s |
| `surprise_2` | `with_external` | `default` | 1 | ❌ | 0.40 | ❌ | 17 | 22.6s |

---
_Generated automatically by ChatOps Benchmark Harness v2_