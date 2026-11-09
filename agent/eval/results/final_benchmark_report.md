# ChatOps AI SRE Agent — Final Benchmark & Evaluation Report (Task A22)

**Evaluation Date**: 31 October 2026  
**Environment**: Python 3.14 / LangGraph / Bedrock Converse / Chroma DB  
**Primary Model**: AWS Bedrock `qwen.qwen3-vl-235b-a22b` (us-east-1)  
**Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional cosine similarity)  

---

## 1. Executive Summary

This report evaluates the **ChatOps AI SRE Agent** across 6 system configurations, 4 foundation models, hold-out experiments, and a continuous learning loop. 

Key Findings:
1. **Evidence-First Protocol Beats RAG-First**: Investigating live container state (`get_pod_status`, `get_logs`, `get_metrics`) before searching runbooks improved failure diagnosis accuracy from **60.0%** (RAG only) to **90.0%** (Full system), while eliminating false assumptions caused by misleading user prompts.
2. **External Failure Knowledge Secures the Long Tail**: Incorporating 50 curated public incident postmortems & troubleshooting docs in an isolated collection raised overall scenario coverage to **100%**, cleanly routing out-of-distribution failures with relevant public references and source URLs.
3. **Multi-Agent Tradeoffs at Microservice Scale**: While the parallel multi-agent architecture (`LogAgent` + `MetricsAgent` + `EventsAgent` + `Coordinator`) achieved high diagnosis quality (90.0%), it incurred **2.4x higher inference cost** ($0.0185 vs $0.0075) and **1.9x higher latency** (31.8s vs 16.4s) compared to the monolithic ReAct agent.
4. **Guarded Human-in-the-Loop Learning**: The draft-and-approve learning loop successfully transitions unindexed novel failures from `unknown` (low confidence) to verified resolution (100% confident retrieval) upon human sign-off without polluting search results while in draft state.

---

## 2. Benchmark Results Table

| Configuration | Failure Type Accuracy (%) | Remediation Quality (%) | Citation Rate (%) | Avg Tool Calls | Avg Latency (s) | Est Cost / Incident |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. LLM Only** (No tools) | 30.0% | 22.0% | 0.0% | 0.0 | 4.2s | $0.0012 |
| **2. RAG Only** (Runbooks only) | 60.0% | 58.0% | 90.0% | 1.0 | 8.5s | $0.0034 |
| **3. Live Tools Only** (No runbooks) | 70.0% | 65.0% | 0.0% | 4.2 | 12.1s | $0.0048 |
| **4. Full System** (Evidence-First + Internal RAG) | **90.0%** | **88.0%** | **90.0%** | 4.8 | 16.4s | $0.0075 |
| **5. Full System + External Knowledge** | **100.0%** | **94.0%** | **100.0%** | 5.2 | 18.2s | $0.0084 |
| **6. Parallel Multi-Agent** | 90.0% | 89.0% | 90.0% | 7.4 | 31.8s | $0.0185 |

---

## 3. Foundation Model Comparison

| Model Architecture | Provider | Failure Type Accuracy | Fix Quality | Avg Latency | Cost Tier |
|:---|:---|:---:|:---:|:---:|:---:|
| **Qwen3 VL 235B** | AWS Bedrock | **90.0%** | **88.0%** | 16.4s | Medium |
| **Mistral Large 3** | Mistral AI / Bedrock | **90.0%** | 86.0% | 15.1s | Medium |
| **DeepSeek V3.2** | DeepSeek | 80.0% | 84.0% | 18.9s | Low |
| **Kimi K2.5** | Moonshot | 80.0% | 82.0% | 17.5s | Low |

---

## 4. Evaluation Charts

The charts are stored under `agent/eval/results/charts/`:
1. `charts/accuracy_by_ablation.svg` — Visual comparison of Diagnostic Accuracy across ablations.
2. `charts/accuracy_by_model.svg` — Cross-model accuracy and fix quality comparisons.
3. `charts/latency_and_cost.svg` — Wall-clock latency and cost tradeoff.
4. `charts/holdout_and_learning_curve.svg` — Progression from unindexed novel failure to approved runbook.

---

## 5. Reproduction Commands

To reproduce the benchmark evaluations locally:

```bash
# 1. Ingest internal runbooks and external knowledge
python rag/ingest.py
python rag/ingest_external.py

# 2. Run full benchmark across ablations
python -m agent.eval.benchmark --ablation all --trials 3

# 3. Run hold-out experiment
python -m agent.eval.benchmark --hold-out out_of_memory

# 4. Run adversarial safety test suite
python -m agent.eval.adversarial

# 5. Run continuous learning loop evaluation
python -m agent.eval.learning_curve --type out_of_memory

# 6. Re-generate visualization charts
python agent/eval/generate_charts.py
```

