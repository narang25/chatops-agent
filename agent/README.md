# Agent Module (Person A Ownership)

This directory contains the LLM integration layer for our ChatOps SRE agent.

## Overview

The agent layer connects to LLM backends via LangChain:
- **Primary:** Amazon Bedrock using `ChatBedrockConverse` (e.g. Qwen3 MoE models).
- **Fallback:** Local Ollama using `ChatOllama` (e.g. `llama3.2:1b`).
- **Swapping Models:** Changing one line in `agent/config.yaml` seamlessly switches providers or models without code modifications.

## Files

- [`config.yaml`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/config.yaml): Provider selection (`bedrock` vs `ollama`), model IDs, region, and generation parameters.
- [`llm.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/llm.py):
  - `get_llm()`: Factory function that returns an initialized chat model based on `config.yaml`.
  - `clean_output(message)`: Sanitizer that strips `<think>...</think>` tags and drops reasoning blocks to guarantee raw thoughts never reach the end user.
  - `handle_llm_error(error)`: Translates AWS/IAM/Ollama errors into human-friendly explanations.
- [`scripts/list_models.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/scripts/list_models.py): Queries Bedrock for available text models and inference profiles to confirm exact model IDs.
- [`scripts/smoke_llm.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/scripts/smoke_llm.py): Runs 3 verification tests (Hello test, Tool-calling test, and Reasoning-leak test).

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
If you find a specific model ID (such as `qwen.qwen3-235b-a22b-2507-v1:0` or an inference profile like `us.qwen.qwen3-235b-a22b-2507-v1:0`), update `bedrock.model_id` in `agent/config.yaml`.

### 3. Run LLM Smoke Test Suite
Execute the 3-phase smoke test:
```bash
python agent/scripts/smoke_llm.py
```

The script will run:
1. **Hello Test:** Basic generation and latency check.
2. **Tool-Calling Test:** Binds a dummy `get_service_status` tool and asserts that the model invokes the tool with `service='payment-service'`.
3. **Reasoning-Leak Test:** Verifies that no `<think>` tags or hidden reasoning tokens leak through to user-visible outputs.

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
