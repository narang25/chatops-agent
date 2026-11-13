# ChatOps AI SRE Agent — Practical Hands-On Practice Guide

> **Document ID:** `07-HANDS-ON-PRACTICE`  
> **Target Audience:** Developers & Engineers Preparing for Live Coding and System Design Interviews  
> **Mission:** Prove technical ownership by building, modifying, and debugging the ChatOps codebase independently.

---

## Exercise Index

- [Level 1 (Easy): Add a Custom Health Diagnostic Metric to Payment Service](#exercise-1-easy-add-a-custom-health-diagnostic-metric)
- [Level 2 (Easy): Implement an In-Process Model Latency Benchmark Script](#exercise-2-easy-implement-a-model-latency-benchmark-script)
- [Level 3 (Intermediate): Implement Exponential Backoff Retries in Bedrock LLM Connector](#exercise-3-intermediate-exponential-backoff-retries-in-agentllmpy)
- [Level 4 (Intermediate): Build a New Failure Injection Scenario — Disk Full Simulation](#exercise-4-intermediate-build-a-new-failure-scenario-disk_full)
- [Level 5 (Advanced): Implement Structured JSON Output via Pydantic](#exercise-5-advanced-replace-regex-parsing-with-pydantic-structured-output)
- [Level 6 (Rebuild from Scratch): Rebuild the Semantic Chunking & Chroma Ingestion Engine](#exercise-6-rebuild-rebuild-the-rag-ingestion-pipeline-from-scratch)

---

## Exercise 1 (Easy): Add a Custom Health Diagnostic Metric

### 1. Goal
Add a new Prometheus gauge metric named `app_db_connections_active` to `payment-service` that reports the active database connection count on `GET /metrics`.

### 2. Relevant Files
- [`sample_apps/payment-service/app/metrics.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/metrics.py)
- [`sample_apps/payment-service/app/main.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/sample_apps/payment-service/app/main.py)

### 3. Concepts Tested
- Prometheus client library (`Gauge`)
- Metric labeling by service
- Exposing metrics over HTTP exposition format

### 4. Hints
1. In `metrics.py`, instantiate a `Gauge("app_db_connections_active", "Number of active DB connections", ["service"])`.
2. In `main.py`, update this gauge inside `_get_connection()` or query `pg_stat_activity`.

### 5. Expected Behavior
Running `curl http://localhost:8001/metrics` outputs:
```text
# HELP app_db_connections_active Number of active DB connections
# TYPE app_db_connections_active gauge
app_db_connections_active{service="payment-service"} 1.0
```

<details>
<summary>👉 View Solution</summary>

**In `sample_apps/payment-service/app/metrics.py`:**
```python
app_db_connections_active = Gauge(
    "app_db_connections_active",
    "Number of active DB connections",
    ["service"],
)
```

**In `sample_apps/payment-service/app/main.py`:**
```python
from app.metrics import app_db_connections_active

def _get_connection():
    if faults.db_error:
        raise Exception("Simulated database error (db_error fault is ON)")
    if faults.slow_db:
        time.sleep(3)
    conn = psycopg2.connect(DATABASE_URL)
    app_db_connections_active.labels(service=SERVICE_NAME).inc()
    return conn
```
</details>

---

## Exercise 2 (Easy): Implement a Model Latency Benchmark Script

### 1. Goal
Write a standalone Python script in `agent/scripts/benchmark_latency.py` that sends a fixed prompt to the configured LLM 5 times, records each latency duration, and prints the min, max, average, and p95 latency.

### 2. Relevant Files
- [`agent/llm.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/llm.py)
- [`agent/config.yaml`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/config.yaml)

### 3. Concepts Tested
- Foundation model instantiation via `get_llm()`
- Accurate wall-clock timing using `time.perf_counter()`
- Statistical percentile calculation

### 4. Hints
Use `time.perf_counter()` before and after `llm.invoke([HumanMessage(content="Ping")])`. Sort the latency list to calculate percentiles.

<details>
<summary>👉 View Solution</summary>

```python
#!/usr/bin/env python3
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import HumanMessage
from agent.llm import get_llm

def benchmark_llm(iterations: int = 5):
    llm = get_llm()
    latencies = []
    print(f"Running {iterations} latency trials against {llm.model_id}...")

    for i in range(1, iterations + 1):
        t0 = time.perf_counter()
        resp = llm.invoke([HumanMessage(content="Explain DNS in 10 words.")])
        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)
        print(f"  Trial {i}: {elapsed:.3f}s")

    latencies.sort()
    avg_lat = sum(latencies) / len(latencies)
    p95_lat = latencies[int(len(latencies) * 0.95)]

    print("\n--- Benchmark Summary ---")
    print(f"Min: {latencies[0]:.3f}s | Max: {latencies[-1]:.3f}s | Avg: {avg_lat:.3f}s | P95: {p95_lat:.3f}s")

if __name__ == "__main__":
    benchmark_llm()
```
</details>

---

## Exercise 3 (Intermediate): Implement Exponential Backoff Retries in `agent/llm.py`

### 1. Goal
Modify `ChatBedrockConverseFallback._generate()` in `agent/llm.py` to automatically retry up to 3 times with exponential backoff if AWS returns a `ThrottlingException` (HTTP 429) or `InternalServerError` (HTTP 500).

### 2. Relevant Files
- [`agent/llm.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/llm.py)

### 3. Concepts Tested
- Subclassing LangChain ChatModels
- Error code extraction from `botocore.exceptions.ClientError`
- Exponential backoff algorithm ($t = \text{base} \times 2^{\text{attempt}} + \text{jitter}$)

### 4. Expected Behavior
If Bedrock throttles requests during high-concurrency benchmarks, the model retries automatically with increasing delay (e.g. 1s, 2s, 4s) instead of failing immediately.

<details>
<summary>👉 View Solution</summary>

```python
import random
import time
from botocore.exceptions import ClientError

def _generate_with_retry(self, messages, stop=None, run_manager=None, **kwargs):
    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries + 1):
        try:
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("ThrottlingException", "TooManyRequestsException", "InternalServerException") and attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                print(f"[Retry Warning] Bedrock {code}. Retrying in {delay:.2f}s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
            else:
                raise
```
</details>

---

## Exercise 4 (Intermediate): Build a New Failure Scenario — Disk Full

### 1. Goal
Create a new failure injection script `infra/failures/disk_full.py` that:
1. Writes a 100MB dummy file to a container's `/tmp` directory to simulate disk exhaustion.
2. Captures container logs containing `[Errno 28] No space left on device`.
3. Outputs ground-truth files `diskfull-order-001.jsonl` and `diskfull-order-001.meta.json` in `data/incident_logs/`.

### 2. Relevant Files
- [`infra/failures/run_scenario.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/infra/failures/run_scenario.py)
- [`data/runbooks/disk_full-any.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/data/runbooks/disk_full-any.md)

### 3. Concepts Tested
- Chaos engineering principles
- Container filesystem inspection via `docker exec`
- Contract adherence to `contracts/incident_meta.md`

<details>
<summary>👉 View Solution</summary>

```python
#!/usr/bin/env python3
import json
import os
import subprocess
import time
from datetime import datetime, timezone

SCENARIO_ID = "diskfull-order-001"
CONTAINER_NAME = "order-service"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.path.join(REPO_ROOT, "data", "incident_logs")

def main():
    print(f"Injecting failure: {SCENARIO_ID}...")
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Fill disk in container
    subprocess.run(["docker", "exec", CONTAINER_NAME, "sh", "-c", "dd if=/dev/zero of=/tmp/bigfile bs=1M count=100"], check=False)
    
    # Generate log entry
    now = datetime.now(timezone.utc).isoformat()
    log_line = {
        "timestamp": now,
        "service": "order-service",
        "level": "CRITICAL",
        "message": "[Errno 28] No space left on device while writing cache"
    }
    
    with open(os.path.join(LOG_DIR, f"{SCENARIO_ID}.jsonl"), "w") as f:
        f.write(json.dumps(log_line) + "\n")
        
    meta = {
        "scenario_id": SCENARIO_ID,
        "service": "order-service",
        "failure_type": "disk_full",
        "root_cause": "Ephemeral storage exhausted by temporary files in /tmp",
        "expected_fix": "Clear temporary files and expand volume allocation",
        "signals": ["[Errno 28] No space left on device"]
    }
    with open(os.path.join(LOG_DIR, f"{SCENARIO_ID}.meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"✓ Failure injected and artifacts saved to {LOG_DIR}")

if __name__ == "__main__":
    main()
```
</details>

---

## Exercise 5 (Advanced): Replace Regex Parsing with Pydantic Structured Output

### 1. Goal
Refactor `agent/api.py` to eliminate fragile regular expressions (`_extract_failure_type()`, `_extract_confidence()`). Use LangChain's `.with_structured_output()` to guarantee typed JSON outputs conforming to a Pydantic schema.

### 2. Relevant Files
- [`agent/api.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/api.py)
- [`agent/agent.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/agent/agent.py)

### 3. Concepts Tested
- Pydantic v2 data modeling
- LLM JSON schema constraints (`with_structured_output`)
- Elimination of parsing edge cases

<details>
<summary>👉 View Solution</summary>

```python
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class DiagnosticReport(BaseModel):
    diagnosis: str = Field(description="Clear explanation of the root cause.")
    failure_type: Literal[
        "out_of_memory", "bad_config", "health_check_failure", "db_timeout",
        "dependency_failure", "disk_full", "cpu_saturation", "crash_loop",
        "network_timeout", "high_error_rate", "other", "unknown"
    ]
    confidence: Literal["high", "medium", "low"]
    how_to_confirm: List[str] = Field(description="Verification commands.")
    recommended_fix: List[str] = Field(description="Remediation steps.")
    proposed_action: Optional[str] = Field(description="Action name if applicable.")
    sources: List[str] = Field(description="Cited runbook titles or URLs.")

# In agent builder:
def get_structured_agent():
    llm = get_llm()
    # Forces foundation model to emit strictly validated Pydantic JSON
    return llm.with_structured_output(DiagnosticReport)
```
</details>

---

## Exercise 6 (Rebuild from Scratch): Rebuild the Semantic Chunking & Chroma Ingestion Engine

### 1. Goal
Write a minimal, standalone script `rebuild_rag.py` from scratch (without importing `rag/ingest.py`) that:
1. Reads all Markdown files in `data/runbooks/`.
2. Parses frontmatter title and failure_type.
3. Splits documents by `## ` headers.
4. Initializes a local Chroma client with `all-MiniLM-L6-v2`.
5. Ingests all chunks using deterministic chunk IDs.
6. Performs a verification query: `"container killed out of memory"`.

### 2. Verification Criteria
Running `python rebuild_rag.py` outputs the chunk count and confirms that `out_of_memory-payment.md` ranks #1 with similarity score $> 0.70$.

<details>
<summary>👉 View Solution</summary>

```python
#!/usr/bin/env python3
import re
from pathlib import Path
import frontmatter
import chromadb
from chromadb.utils import embedding_functions

def run_rebuild():
    repo_root = Path(__file__).resolve().parent.parent
    runbooks_dir = repo_root / "data" / "runbooks"
    db_path = repo_root / "chroma_db_rebuild"
    db_path.mkdir(exist_ok=True)

    client = chromadb.PersistentClient(path=str(db_path))
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    collection = client.get_or_create_collection(name="runbooks_rebuild", embedding_function=embed_fn)

    ids, docs, metas = [], [], []

    for md_file in runbooks_dir.glob("*.md"):
        post = frontmatter.load(md_file)
        if post.get("status") == "draft":
            continue
            
        title = post.get("title", md_file.stem)
        failure_type = post.get("failure_type", "unknown")
        
        # Split on ## headers
        sections = re.split(r"(?m)^##\s+", post.content)
        for idx, sec in enumerate(sections):
            sec = sec.strip()
            if not sec:
                continue
            chunk_id = f"{md_file.stem}::sec::{idx}"
            chunk_doc = f"# {title} ({failure_type})\n\n{sec}"
            ids.append(chunk_id)
            docs.append(chunk_doc)
            metas.append({"title": title, "failure_type": failure_type, "source": str(md_file.name)})

    collection.upsert(ids=ids, documents=docs, metadatas=metas)
    print(f"Indexed {len(ids)} chunks successfully into {db_path.name}.")

    # Verify query
    query = "container killed out of memory"
    results = collection.query(query_texts=[query], n_results=1)
    top_title = results["metadatas"][0][0]["title"]
    dist = results["distances"][0][0]
    score = 1.0 / (1.0 + dist)
    print(f"\nQuery: '{query}'\nTop Result: {top_title}\nSimilarity Score: {score:.3f}")

if __name__ == "__main__":
    run_rebuild()
```
</details>
