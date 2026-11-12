# ChatOps Agent Benchmark Report — `benchmark_2026-11-12_cpusat_timing`

- **Timestamp**: 2026-11-12 14:09:41 UTC
- **Ablations Evaluated**: `llm_only`, `full`
- **Models**: `default`
- **Hold-Out Setting**: `None`
- **Total Evaluations**: `4`

## Summary Results

| Configuration | Model | FT Accuracy | Fix Quality | Citation Rate | Avg Tools | Avg Latency | Est Cost / Incident |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `llm_only` | `default` | **0.0%** | 25.0% | 0.0% | 0.0 | 12.33s | $0.0019 |
| `full` | `default` | **100.0%** | 62.5% | 100.0% | 13.0 | 26.66s | $0.0144 |

## Evaluation Details

| Scenario | Ablation | Model | Trial | FT Match | Fix Score | RB Cited | Tools | Latency |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `cpusat-payment-001` | `llm_only` | `default` | 1 | ❌ | 0.25 | ❌ | 0 | 13.5s |
| `cpusat-payment-001` | `llm_only` | `default` | 2 | ❌ | 0.25 | ❌ | 0 | 11.2s |
| `cpusat-payment-001` | `full` | `default` | 1 | ✅ | 0.50 | ✅ | 13 | 31.6s |
| `cpusat-payment-001` | `full` | `default` | 2 | ✅ | 0.75 | ✅ | 13 | 21.7s |

---
_Generated automatically by ChatOps Benchmark Harness v2_