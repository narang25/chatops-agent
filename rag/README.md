# RAG Ingestion Module (Person A Ownership)

This directory contains the knowledge ingestion pipeline for our ChatOps agent. It loads structured Markdown runbooks, chunks them with section metadata, generates local embeddings, and stores them in Chroma DB.

## Overview

- **Input Data**: Markdown runbooks in [`data/runbooks/`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/data/runbooks/) conforming to [`contracts/runbook_format.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/contracts/runbook_format.md) and [`contracts/failure_types.md`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/contracts/failure_types.md).
- **Chunking Strategy**:
  - Splits documents by section headings (`## Symptoms`, `## Likely cause`, `## How to confirm`, `## Fix`, `## Prevention`).
  - Sections exceeding 600 characters are sub-chunked with a 100-character overlap along sentence/newline boundaries.
  - Prepends title, service, and section headers to each chunk to retain semantic context.
- **Embedding Model**: `sentence-transformers` with `all-MiniLM-L6-v2` (384 dimensions, local execution, free, zero cloud API dependencies).
- **Vector Database**: Chroma DB persisted at `chroma_db/` (gitignored).
- **Idempotence**: Uses deterministic IDs (`<runbook>::<section>::<chunk_idx>`) so re-running ingestion updates existing records without duplicate accumulation.

---

## Files

- [`ingest.py`](file:///Users/nikhi/Desktop/Chatops/chatops-agent/rag/ingest.py): Main ingestion script with built-in retrieval verification.
- `data/runbooks/`: 6 concrete incident runbooks matching Person B's sample services and failure signatures:
  1. `out_of_memory-payment.md` (`out_of_memory`, `payment-service`)
  2. `bad_config-order.md` (`bad_config`, `order-service`)
  3. `health_check_failure-inventory.md` (`health_check_failure`, `inventory-service`)
  4. `db_timeout-payment.md` (`db_timeout`, `payment-service`)
  5. `dependency_failure-order.md` (`dependency_failure`, `order-service`)
  6. `cpu_saturation-any.md` (`cpu_saturation`, `any`)

---

## How to Run

### 1. Ingest All Runbooks & Run Verification
From the repository root (`chatops-agent/`):
```bash
python rag/ingest.py
```
This parses the 6 runbooks, builds 32 chunks in Chroma, and runs an automated verification search for `"container killed out of memory"`, asserting that `out_of_memory-payment.md` is returned as the #1 result.

### 2. Run Ad-Hoc Similarity Searches
Search the runbooks collection directly via the CLI:
```bash
python rag/ingest.py --query "missing environment variable PAYMENT_SERVICE_URL"
python rag/ingest.py --query "database connection timed out after 5s"
python rag/ingest.py --query "health check 500 internal server error"
```
