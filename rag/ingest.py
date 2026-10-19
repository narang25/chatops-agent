#!/usr/bin/env python3
"""
Runbook Ingestion Script for ChatOps Agent.

Parses Markdown runbooks in data/runbooks/, reads YAML front-matter,
chunks documents by section headings (falling back to ~600 chars with ~100 overlap),
embeds using sentence-transformers (all-MiniLM-L6-v2), and persists to Chroma DB at chroma_db/.

Idempotent: Re-running this script updates existing chunks without creating duplicates.
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add repository root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from chromadb.utils import embedding_functions
    import frontmatter
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Please activate your virtual environment: `source .venv/bin/activate`")
    sys.exit(1)

# Default paths
DEFAULT_RUNBOOKS_DIR = PROJECT_ROOT / "data" / "runbooks"
DEFAULT_DB_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "runbooks"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def split_into_sections(markdown_text: str) -> List[Tuple[str, str]]:
    """
    Splits markdown content by '## Section Title' headers.
    Returns a list of (section_title, section_body) tuples.
    """
    pattern = r"(?m)^##\s+(.+)$"
    matches = list(re.finditer(pattern, markdown_text))

    if not matches:
        return [("Overview", markdown_text.strip())]

    sections: List[Tuple[str, str]] = []

    # Content before first ## heading (if any)
    intro = markdown_text[: matches[0].start()].strip()
    if intro:
        sections.append(("Overview", intro))

    for i, match in enumerate(matches):
        section_title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        body = markdown_text[start:end].strip()
        sections.append((section_title, body))

    return sections


def subchunk_text(text: str, max_chars: int = 600, overlap: int = 100) -> List[str]:
    """
    Splits text exceeding max_chars into overlapping sub-chunks.
    Prefers breaking on newlines, periods, or spaces.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    chunks: List[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + max_chars, text_len)
        if end >= text_len:
            chunks.append(text[start:].strip())
            break

        # Attempt to split on newline or sentence boundary
        split_pt = text.rfind("\n", start, end)
        if split_pt == -1 or split_pt <= start + 100:
            split_pt = text.rfind(". ", start, end)
            if split_pt != -1:
                split_pt += 1  # include period
        if split_pt == -1 or split_pt <= start + 100:
            split_pt = text.rfind(" ", start, end)
        if split_pt == -1 or split_pt <= start:
            split_pt = end

        chunk = text[start:split_pt].strip()
        if chunk:
            chunks.append(chunk)

        # Move forward taking overlap into account
        start = max(start + 1, split_pt - overlap)

    return chunks


def process_runbook(filepath: Path) -> List[Dict[str, Any]]:
    """
    Loads a runbook file, extracts front-matter, and generates structured chunks.
    """
    post = frontmatter.load(filepath)
    title = str(post.get("title", filepath.stem))
    failure_type = str(post.get("failure_type", "unknown"))
    service = str(post.get("service", "any"))
    severity = str(post.get("severity", "medium"))

    # Relative source path for clean, portable references
    try:
        source_rel = str(filepath.relative_to(PROJECT_ROOT))
    except ValueError:
        source_rel = str(filepath)

    sections = split_into_sections(post.content)
    chunks: List[Dict[str, Any]] = []

    for sec_idx, (section_title, section_body) in enumerate(sections):
        sub_chunks = subchunk_text(section_body, max_chars=600, overlap=100)
        for sub_idx, sub_text in enumerate(sub_chunks):
            # Deterministic chunk ID prevents duplicates on re-indexing
            chunk_id = f"{filepath.stem}::{section_title}::{sub_idx}"

            # Format enriched document text incorporating context
            enriched_document = (
                f"# Runbook: {title}\n"
                f"Service: {service} | Failure Type: {failure_type}\n"
                f"## {section_title}\n\n"
                f"{sub_text}"
            )

            metadata = {
                "title": title,
                "source": source_rel,
                "failure_type": failure_type,
                "service": service,
                "section": section_title,
                "severity": severity,
            }

            chunks.append({
                "id": chunk_id,
                "document": enriched_document,
                "metadata": metadata,
            })

    return chunks


def get_chroma_collection(db_path: Path):
    """
    Initializes PersistentClient and returns the Chroma collection
    with sentence-transformers (all-MiniLM-L6-v2) embedding function.
    """
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "ChatOps SRE Runbooks Collection"},
    )
    return client, collection


def ingest_runbooks(runbooks_dir: Path, db_path: Path) -> int:
    """
    Scans runbooks_dir, processes all *.md runbooks, and upserts chunks into Chroma.
    """
    runbook_files = sorted(list(runbooks_dir.glob("*.md")))
    if not runbook_files:
        print(f"Warning: No Markdown runbooks found in {runbooks_dir}")
        return 0

    print("=" * 70)
    print("ChatOps Runbook Ingestion (Sentence-Transformers + Chroma)")
    print(f"Runbooks Dir: {runbooks_dir}")
    print(f"Chroma DB:    {db_path}")
    print(f"Embedding:    {EMBEDDING_MODEL_NAME} (local, no AWS dependency)")
    print("=" * 70)

    client, collection = get_chroma_collection(db_path)

    all_ids: List[str] = []
    all_documents: List[str] = []
    all_metadatas: List[Dict[str, Any]] = []

    print(f"Processing {len(runbook_files)} runbooks:")
    for filepath in runbook_files:
        chunks = process_runbook(filepath)
        print(f"  * {filepath.name:<35} -> {len(chunks)} chunk(s)")
        for c in chunks:
            all_ids.append(c["id"])
            all_documents.append(c["document"])
            all_metadatas.append(c["metadata"])

    print("-" * 70)
    print(f"Total chunks to upsert: {len(all_ids)}")

    start_time = time.perf_counter()
    # Upsert ensures idempotent re-indexing: existing chunk IDs are updated, never duplicated
    collection.upsert(
        ids=all_ids,
        documents=all_documents,
        metadatas=all_metadatas,
    )
    elapsed = time.perf_counter() - start_time

    print(f"✓ Successfully indexed into Chroma in {elapsed:.2f}s.")
    print(f"✓ Total active collection count: {collection.count()} chunks.\n")
    return len(all_ids)


def query_runbooks(
    query: str,
    db_path: Path = DEFAULT_DB_PATH,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Retrieves top_k relevant runbook snippets for a query.
    Used for verification and RAG retrieval.
    """
    _, collection = get_chroma_collection(db_path)
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    formatted_results: List[Dict[str, Any]] = []
    if not results or not results["ids"] or not results["ids"][0]:
        return formatted_results

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

    for doc, meta, dist in zip(docs, metas, distances):
        # Convert L2 distance to normalized similarity score (0 to 1)
        score = round(1.0 / (1.0 + float(dist)), 4)
        formatted_results.append({
            "title": meta.get("title", ""),
            "source": meta.get("source", ""),
            "failure_type": meta.get("failure_type", ""),
            "service": meta.get("service", ""),
            "section": meta.get("section", ""),
            "score": score,
            "snippet": doc,
        })

    return formatted_results


def run_verification(db_path: Path) -> bool:
    """
    Verifies that a similarity search for 'container killed out of memory'
    ranks the OOM runbook first, per Task A2 specification.
    """
    test_query = "container killed out of memory"
    print("=" * 70)
    print(f"Running Retrieval Verification Query: \"{test_query}\"")
    print("=" * 70)

    results = query_runbooks(test_query, db_path=db_path, top_k=3)

    if not results:
        print("✗ FAIL: Verification query returned 0 results.")
        return False

    print(f"{'Rank':<5} | {'Score':<7} | {'Failure Type':<18} | {'Service':<17} | {'Title'}")
    print("-" * 80)
    for idx, r in enumerate(results, start=1):
        print(f"#{idx:<4} | {r['score']:<7} | {r['failure_type']:<18} | {r['service']:<17} | {r['title']}")

    top_match = results[0]
    is_oom = top_match["failure_type"] == "out_of_memory"
    print("\nSnippet preview from top match:")
    snippet_preview = top_match["snippet"].replace("\n", " ")[:160] + "..."
    print(f"  \"{snippet_preview}\"")

    if is_oom:
        print("\n✓ PASS: Top-1 match is the Out of Memory (OOM) runbook!")
        return True
    else:
        print(f"\n✗ FAIL: Expected top match 'out_of_memory', but got '{top_match['failure_type']}'")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest runbooks into Chroma vector database.")
    parser.add_argument(
        "--runbooks-dir",
        type=Path,
        default=DEFAULT_RUNBOOKS_DIR,
        help="Path to folder containing markdown runbooks",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to persistent Chroma DB storage",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip the post-ingest retrieval verification query",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Run an ad-hoc similarity search query against the collection",
    )

    args = parser.parse_args()

    # If ad-hoc query is requested, run search and exit
    if args.query:
        print(f"Searching for: '{args.query}' (top 3):")
        hits = query_runbooks(args.query, db_path=args.db_path, top_k=3)
        for i, hit in enumerate(hits, 1):
            print(f"\n[{i}] {hit['title']} ({hit['failure_type']}) - Score: {hit['score']}")
            print(f"    Source: {hit['source']} (Section: {hit['section']})")
            print(f"    {hit['snippet'][:200]}...")
        return

    # Ingest runbooks
    total_chunks = ingest_runbooks(args.runbooks_dir, args.db_path)
    if total_chunks == 0:
        sys.exit(1)

    # Post-ingestion verification check
    if not args.skip_verify:
        passed = run_verification(args.db_path)
        if not passed:
            sys.exit(1)


if __name__ == "__main__":
    main()
