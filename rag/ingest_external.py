#!/usr/bin/env python3
"""
External Failure Knowledge Ingestion Script (Week 4 -- Task A17).
================================================================

Indexes curated real-world failure postmortems and official troubleshooting
docs (Kubernetes, PostgreSQL, Docker, Prometheus, Cloud outages) into a
SEPARATE Chroma collection named `external_knowledge`.

Collection separation guarantees that internal runbooks are never contaminated,
while allowing the agent to reference similar public incidents for out-of-distribution
or novel failures.

Usage:
    python rag/ingest_external.py            # Ingest all external docs
    python rag/ingest_external.py --verify   # Ingest and run sample verification
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    import frontmatter
    from chromadb.utils import embedding_functions
except ImportError as err:
    print(f"Error importing dependencies: {err}")
    print("Please activate your virtual environment: source .venv/bin/activate")
    sys.exit(1)

from rag.ingest import split_into_sections, subchunk_text

# Paths and collection naming
DEFAULT_EXTERNAL_DIR = PROJECT_ROOT / "data" / "external"
DEFAULT_DB_PATH = PROJECT_ROOT / "chroma_db"
EXTERNAL_COLLECTION_NAME = "external_knowledge"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def get_external_chroma_collection(db_path: Path = DEFAULT_DB_PATH):
    """
    Initializes PersistentClient and returns the 'external_knowledge' Chroma collection.
    Uses sentence-transformers (all-MiniLM-L6-v2) embedding function.
    """
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    collection = client.get_or_create_collection(
        name=EXTERNAL_COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "External SRE postmortems and troubleshooting docs"},
    )
    return client, collection


def process_external_doc(filepath: Path) -> list[dict[str, Any]]:
    """
    Loads an external failure markdown file, extracts YAML frontmatter,
    and splits into structured chunks by section.
    """
    post = frontmatter.load(filepath)
    title = str(post.get("title", filepath.stem))
    failure_type = str(post.get("failure_type", "other"))
    source_type = str(post.get("source_type", "external_doc"))
    source_url = str(post.get("source_url", ""))
    license_type = str(post.get("license", "Unknown"))
    status = str(post.get("status", "summary"))

    try:
        source_rel = str(filepath.relative_to(PROJECT_ROOT))
    except ValueError:
        source_rel = str(filepath)

    sections = split_into_sections(post.content)
    chunks: list[dict[str, Any]] = []

    for section_title, section_body in sections:
        sub_chunks = subchunk_text(section_body, max_chars=600, overlap=100)
        for sub_idx, sub_text in enumerate(sub_chunks):
            chunk_id = f"ext::{filepath.stem}::{section_title}::{sub_idx}"

            enriched_document = (
                f"# External Knowledge: {title}\n"
                f"Source: {source_url} | Type: {source_type} | Failure Type: {failure_type} | License: {license_type}\n"
                f"## {section_title}\n\n"
                f"{sub_text}"
            )

            metadata = {
                "title": title,
                "source": source_rel,
                "failure_type": failure_type,
                "source_type": source_type,
                "source_url": source_url,
                "license": license_type,
                "status": status,
                "section": section_title,
            }

            chunks.append({
                "id": chunk_id,
                "document": enriched_document,
                "metadata": metadata,
            })

    return chunks


def ingest_external_docs(
    external_dir: Path = DEFAULT_EXTERNAL_DIR,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """
    Scans external_dir, processes all *.md documents, and upserts into 'external_knowledge' collection.
    Idempotent: updates existing chunks without creating duplicates.
    """
    doc_files = sorted(external_dir.glob("*.md"))
    if not doc_files:
        print(f"Warning: No external Markdown documents found in {external_dir}")
        return 0

    print("=" * 70)
    print("External Knowledge Ingestion (Sentence-Transformers + Chroma)")
    print(f"External Dir: {external_dir}")
    print(f"Chroma DB:    {db_path}")
    print(f"Collection:   {EXTERNAL_COLLECTION_NAME}")
    print(f"Embedding:    {EMBEDDING_MODEL_NAME} (local, all-MiniLM-L6-v2)")
    print("=" * 70)

    client, collection = get_external_chroma_collection(db_path)

    all_ids: list[str] = []
    all_documents: list[str] = []
    all_metadatas: list[dict[str, Any]] = []

    print(f"Processing {len(doc_files)} external failure documents:")
    for filepath in doc_files:
        chunks = process_external_doc(filepath)
        for c in chunks:
            all_ids.append(c["id"])
            all_documents.append(c["document"])
            all_metadatas.append(c["metadata"])

    print("-" * 70)
    print(f"Total external chunks to upsert: {len(all_ids)}")

    t0 = time.perf_counter()
    collection.upsert(
        ids=all_ids,
        documents=all_documents,
        metadatas=all_metadatas,
    )
    elapsed = time.perf_counter() - t0

    print(f"✓ Successfully indexed external knowledge into Chroma in {elapsed:.2f}s.")
    print(f"✓ Total active external collection count: {collection.count()} chunks.\n")
    return len(all_ids)


def query_external_docs(
    query: str,
    db_path: Path = DEFAULT_DB_PATH,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Queries the 'external_knowledge' collection for similar public incidents and docs.
    Returns formatted results with source_type and source_url.
    """
    _, collection = get_external_chroma_collection(db_path)
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    formatted_results: list[dict[str, Any]] = []
    if not results or not results["ids"] or not results["ids"][0]:
        return formatted_results

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

    for doc, meta, dist in zip(docs, metas, distances):
        score = round(1.0 / (1.0 + float(dist)), 4)
        formatted_results.append({
            "title": meta.get("title", ""),
            "source": meta.get("source", ""),
            "failure_type": meta.get("failure_type", "other"),
            "service": "external",
            "section": meta.get("section", ""),
            "score": score,
            "snippet": doc,
            "source_type": meta.get("source_type", "external_doc"),
            "url": meta.get("source_url", ""),
            "license": meta.get("license", ""),
        })

    return formatted_results


def run_verification(db_path: Path = DEFAULT_DB_PATH) -> bool:
    """Verifies that external queries return properly tagged external results."""
    print("Running external knowledge verification test...")
    test_query = "CoreDNS CrashLoopBackOff infinite forwarding loop"
    results = query_external_docs(test_query, db_path=db_path, top_k=1)
    if not results:
        print("✗ FAILED: No results returned for test query.")
        return False

    top_hit = results[0]
    print(f"Query:        '{test_query}'")
    print(f"Top Hit:      {top_hit['title']}")
    print(f"Score:        {top_hit['score']}")
    print(f"Source Type:  {top_hit['source_type']}")
    print(f"URL:          {top_hit['url']}")

    if "coredns" in top_hit["title"].lower() and top_hit["url"]:
        print("✓ PASS: Verification succeeded.\n")
        return True
    print("✗ FAILED: Top hit did not match expected CoreDNS document.\n")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest external SRE failure knowledge into Chroma")
    parser.add_argument("--external-dir", type=Path, default=DEFAULT_EXTERNAL_DIR)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--verify", action="store_true", help="Run verification check after ingestion")
    args = parser.parse_args()

    ingest_external_docs(args.external_dir, args.db_path)
    if args.verify:
        success = run_verification(args.db_path)
        sys.exit(0 if success else 1)
