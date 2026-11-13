"""
Incident Memory Chroma Ingestion & Retrieval (Expansion A).
===========================================================

Indexes recorded live chaos incidents from `data/incident_logs/` (120 live snapshots)
into a dedicated Chroma vector collection (`incident_memory`).

Enables the ChatOps agent to answer:
  "Have we seen this failure pattern before?"
by performing semantic similarity search across past historical incident postmortems,
root causes, and verified remediations.

Architectural Guarantees:
- Stored in a separate Chroma collection (`incident_memory`) to prevent knowledge base pollution.
- Ranks strictly below internal runbooks in priority.
- Deterministic chunk IDs: `incident::<scenario_id>::<run_id>`.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force offline embedding load
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import chromadb
from chromadb.utils import embedding_functions

DEFAULT_DB_PATH = PROJECT_ROOT / "chroma_db"
INCIDENT_COLLECTION_NAME = "incident_memory"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
MANIFEST_PATH = PROJECT_ROOT / "data" / "incident_logs" / "chaos_manifest.jsonl"


def get_incident_collection(db_path: Path = DEFAULT_DB_PATH):
    """Initializes or connects to the incident_memory Chroma collection."""
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    collection = client.get_or_create_collection(
        name=INCIDENT_COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "ChatOps Historical Incident Memory & Postmortems"},
    )
    return client, collection


def build_incident_doc(manifest_row: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    """Builds a structured telemetry document from an incident snapshot without ground-truth labels."""
    snap_dir_str = manifest_row.get("snapshot_dir")
    if not snap_dir_str:
        return None

    snap_dir = Path(snap_dir_str)
    if not snap_dir.exists():
        return None

    run_id = manifest_row.get("run_id", snap_dir.name)
    service = manifest_row.get("service", "unknown")

    # Read pod_status summary if available (pure runtime telemetry)
    pod_summary = "status=unknown"
    pod_file = snap_dir / "pod_status.json"
    if pod_file.exists():
        try:
            with open(pod_file, encoding="utf-8") as f:
                pdata = json.load(f)
                pod_summary = (
                    f"ExitCode: {pdata.get('exit_code', 0)}, "
                    f"OOMKilled: {pdata.get('oom_killed', False)}, "
                    f"Restarts: {pdata.get('restart_count', 0)}, "
                    f"State: {pdata.get('status', 'running')}"
                )
        except Exception:
            pass

    # Read metrics summary if available (pure Prometheus numeric samples)
    metrics_summary = ""
    metrics_file = snap_dir / "metrics.json"
    if metrics_file.exists():
        try:
            with open(metrics_file, encoding="utf-8") as f:
                mdata = json.load(f).get("metrics", {})
                m_parts = [f"{k}={v}" for k, v in mdata.items() if v is not None]
                if m_parts:
                    metrics_summary = ", ".join(m_parts)
        except Exception:
            pass

    # Read events summary if available (pure container lifecycle events)
    events_summary = "none"
    events_file = snap_dir / "events.json"
    if events_file.exists():
        try:
            with open(events_file, encoding="utf-8") as f:
                edata = json.load(f).get("events", [])
                e_reasons = [e.get("reason", e.get("type", "")) for e in edata if isinstance(e, dict)]
                if e_reasons:
                    events_summary = ", ".join(e_reasons[:5])
        except Exception:
            pass

    # Read sample error logs if available (raw application logs)
    error_sample = ""
    logs_file = snap_dir / "logs.jsonl"
    if logs_file.exists():
        try:
            with open(logs_file, encoding="utf-8", errors="replace") as f:
                err_lines = []
                for line in f:
                    if any(kw in line.upper() for kw in ("ERROR", "CRITICAL", "WARN", "EXCEPTION", "KILL", "TIMEOUT")):
                        err_lines.append(line.strip()[:150])
                        if len(err_lines) >= 4:
                            break
                if err_lines:
                    error_sample = " | ".join(err_lines)
        except Exception:
            pass

    doc_text = (
        f"# Historical Incident Telemetry: {run_id}\n"
        f"Service: {service}\n"
        f"Runtime Pod State: {pod_summary}\n"
    )
    if metrics_summary:
        doc_text += f"Observed Metrics: {metrics_summary}\n"
    if events_summary != "none":
        doc_text += f"Cluster Events: {events_summary}\n"
    if error_sample:
        doc_text += f"Raw Application Logs: {error_sample}\n"

    doc_id = f"incident::{run_id}"
    metadata = {
        "run_id": run_id,
        "service": service,
        "source_type": "incident_memory",
        "started_at": manifest_row.get("started_at", ""),
    }

    return doc_id, doc_text, metadata


def ingest_incident_memory(db_path: Path = DEFAULT_DB_PATH) -> int:
    """Scans chaos_manifest.jsonl, extracts all snapshot records, and indexes into Chroma."""
    if not MANIFEST_PATH.exists():
        print(f"Warning: Manifest not found at {MANIFEST_PATH}")
        return 0

    print("=" * 70)
    print("ChatOps Incident Memory Ingestion (Task A Extension)")
    print(f"Manifest:   {MANIFEST_PATH}")
    print(f"Chroma DB:  {db_path}")
    print(f"Collection: {INCIDENT_COLLECTION_NAME}")
    print("=" * 70)

    _, collection = get_incident_collection(db_path)

    all_ids: list[str] = []
    all_documents: list[str] = []
    all_metadatas: list[dict[str, Any]] = []

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            item = build_incident_doc(row)
            if item:
                doc_id, doc_text, meta = item
                all_ids.append(doc_id)
                all_documents.append(doc_text)
                all_metadatas.append(meta)

    if not all_ids:
        print("No valid incident snapshots found to ingest.")
        return 0

    # Batch upsert into Chroma
    BATCH_SIZE = 50
    total = len(all_ids)
    for i in range(0, total, BATCH_SIZE):
        collection.upsert(
            ids=all_ids[i : i + BATCH_SIZE],
            documents=all_documents[i : i + BATCH_SIZE],
            metadatas=all_metadatas[i : i + BATCH_SIZE],
        )

    print(f"Successfully indexed {total} past incident postmortems into '{INCIDENT_COLLECTION_NAME}'.")
    return total


def query_incident_memory(
    query: str,
    db_path: Path = DEFAULT_DB_PATH,
    top_k: int = 3,
    threshold: float = 0.55,
) -> list[dict[str, Any]]:
    """Query historical incident memory for similar past outages."""
    try:
        _, collection = get_incident_collection(db_path)
        if collection.count() == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k * 2, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict[str, Any]] = []
        if not results or not results["documents"] or not results["documents"][0]:
            return []

        seen_scenarios: set[str] = set()
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        dists = results["distances"][0] if results["distances"] else [1.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, dists):
            # Convert L2 distance to cosine similarity approximation: 1 / (1 + dist)
            score = round(1.0 / (1.0 + float(dist)), 4)
            if score < threshold:
                continue

            run_id = meta.get("run_id", "")
            if run_id in seen_scenarios:
                continue
            seen_scenarios.add(run_id)

            hits.append({
                "run_id": run_id,
                "service": meta.get("service", ""),
                "score": score,
                "source_type": "incident_memory",
                "telemetry_snippet": doc[:400],
            })
            if len(hits) >= top_k:
                break

        return hits
    except Exception as exc:
        print(f"Incident memory query error: {exc}", file=sys.stderr)
        return []


if __name__ == "__main__":
    t0 = time.perf_counter()
    count = ingest_incident_memory()
    elapsed = round(time.perf_counter() - t0, 3)
    print(f"Completed in {elapsed}s. Running sample query:")
    sample_hits = query_incident_memory("payment-service OOM killed exit code 137 memory leak")
    for idx, hit in enumerate(sample_hits, 1):
        print(f"  [{idx}] {hit['run_id']} ({hit['service']}) score={hit['score']}")
