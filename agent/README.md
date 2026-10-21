# Agent Module (Person A Ownership)

This directory contains the LLM integration layer for our ChatOps SRE agent.

## Overview

The agent layer connects to LLM backends via LangChain:
- **Primary:** Amazon Bedrock using `ChatBedrockConverse` (supports Qwen, Moonshot, Z.AI, Mistral, etc.).
- **Fallback:** Local Ollama using `ChatOllama` (e.g. `llama3.2:1b`).
- **Automatic Fallback:** In `agent/llm.py`, if a plain model ID raises `ValidationException` (common for models requiring cross-region inference profiles), it automatically retries with the `us.` prefix (e.g. `us.moonshotai.kimi-k3`) and reports which ID succeeded.
- **Swapping Models:** Changing one line in `agent/config.yaml` or passing `--model-id` via CLI switches models seamlessly.

## Files

- [`config.yaml`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/config.yaml): Provider selection (`bedrock` vs `ollama`), default model IDs, region, and generation parameters.
- [`llm.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/llm.py):
  - `get_llm(model_id=None)`: Factory function returning an initialized chat model based on `config.yaml` or optional model override.
  - `clean_output(message)`: Sanitizer that strips `<think>...</think>` tags and drops reasoning blocks to guarantee raw thoughts never reach the end user.
  - `handle_llm_error(error)`: Translates AWS/IAM/Ollama errors into human-friendly explanations.
  - `ChatBedrockConverseFallback`: Automatically catches `ValidationException` and retries once with the `us.` prefix.
- [`scripts/list_models.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/scripts/list_models.py): Queries Bedrock for available text models and inference profiles to confirm exact model IDs.
- [`scripts/smoke_llm.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/scripts/smoke_llm.py): Runs 3 verification tests (Hello test, Tool-calling test, and Reasoning-leak test). Supports `--model-id <ID>` override.
- [`scripts/compare_models.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/scripts/compare_models.py): Benchmarks candidate models across generation, tool-calling, and reasoning leaks, printing a summary table and saving to `agent/scripts/results/model_comparison.json`.

---

## How to Run

### 1. Activate Virtual Environment
From the repository root (`chatops-agent/`):
```bash
source .venv/bin/activate
```

### 2. Verify Available Bedrock Models
Run the model listing script to find exact model IDs in your region:
```bash
python agent/scripts/list_models.py
```

### 3. Run LLM Smoke Test Suite
Execute the 3-phase smoke test using default config:
```bash
python agent/scripts/smoke_llm.py
```

Or test a specific model directly with the `--model-id` argument:
```bash
python agent/scripts/smoke_llm.py --model-id qwen.qwen3-next-80b-a3b
```

Tests run:
1. **Hello Test:** Basic generation and latency check.
2. **Tool-Calling Test:** Binds a dummy `get_service_status` tool and asserts that the model invokes the tool with `service='payment-service'`.
3. **Reasoning-Leak Test:** Reuses test 1's reply and verifies that no `<think>` tags or hidden reasoning tokens leaked through. If test 1 fails, test 3 marks as `SKIPPED`.

### 4. Benchmark Candidate Models
Compare all 10 candidate models in your Bedrock account:
```bash
python agent/scripts/compare_models.py
```
This tests Hello generation, tool calling, reasoning leakage, and average latency for each candidate, printing a summary table and saving the structured output to `agent/scripts/results/model_comparison.json`.

---

## Switching to Ollama (Local Fallback)

If AWS Bedrock credentials or model access are unavailable:
1. Ensure Ollama is running locally:
   ```bash
   ollama run llama3.2:1b
   ```
2. Edit `agent/config.yaml`:
   ```yaml
   provider: ollama
   ```
3. Re-run the smoke test:
   ```bash
   python agent/scripts/smoke_llm.py
   ```
