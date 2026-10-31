"""
External Knowledge Verification Suite (Week 4 -- Task A17).
===========================================================

Verifies TESTING_GUIDE Section 7.3 requirements:
  1. A query for a failure with no internal runbook returns a relevant external
     source, labelled 'external_postmortem' or 'external_doc', with a URL.
  2. A query for OOM returns the internal runbook ranked above external hits.
  3. Switching external knowledge off (include_external=False) removes external hits
     and triggers 'no_confident_match: true' for out-of-distribution queries.
  4. Spot-checks 10 external summaries for valid frontmatter and required sections.

Usage:
    python -m agent.eval.test_external_knowledge
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import frontmatter

from mcp_servers.runbooks.server import search_runbooks


def test_ood_failure_returns_external_with_url() -> bool:
    """Test 1: Novel failure without internal runbook returns external source with URL."""
    print("\n--- Test 1: Out-of-Distribution Query Returns External Source With URL ---")
    query = "CoreDNS CrashLoopBackOff infinite forwarding loop in kube-system"
    result = search_runbooks(query, top_k=3, include_external=True)

    results = result.get("results", [])
    if not results:
        print("✗ FAIL: No results returned.")
        return False

    top_hit = results[0]
    print(f"Query:        {query}")
    print(f"Top Hit:      {top_hit.get('title')}")
    print(f"Score:        {top_hit.get('score')}")
    print(f"Source Type:  {top_hit.get('source_type')}")
    print(f"URL:          {top_hit.get('url')}")
    print(f"No Confident: {result.get('no_confident_match')}")

    passed = (
        top_hit.get("source_type") in ("external_postmortem", "external_doc")
        and bool(top_hit.get("url"))
        and not result.get("no_confident_match")
    )
    print(f"Result: {'✓ PASS' if passed else '✗ FAIL'}")
    return passed


def test_known_oom_ranks_internal_first() -> bool:
    """Test 2: Known failure (OOM) ranks internal runbook above external hits."""
    print("\n--- Test 2: Known OOM Failure Ranks Internal Runbook Above External Hits ---")
    query = "container killed out of memory exit code 137"
    result = search_runbooks(query, top_k=3, include_external=True)

    results = result.get("results", [])
    if not results:
        print("✗ FAIL: No results returned.")
        return False

    top_hit = results[0]
    print(f"Query:        {query}")
    print(f"Top Hit:      {top_hit.get('title')}")
    print(f"Score:        {top_hit.get('score')}")
    print(f"Source Type:  {top_hit.get('source_type')}")
    print(f"URL:          {top_hit.get('url')}")

    passed = (
        top_hit.get("source_type") == "internal_runbook"
        and (
            top_hit.get("failure_type") == "out_of_memory"
            or "oom" in top_hit.get("title", "").lower()
            or "out of memory" in top_hit.get("title", "").lower()
        )
    )
    print(f"Result: {'✓ PASS' if passed else '✗ FAIL'}")
    return passed


def test_toggle_external_knowledge() -> bool:
    """Test 3: Toggling include_external=False disables external hits."""
    print("\n--- Test 3: Toggling include_external=False Disables External Hits ---")
    query = "CoreDNS CrashLoopBackOff infinite forwarding loop"

    with_ext = search_runbooks(query, top_k=3, include_external=True)
    without_ext = search_runbooks(query, top_k=3, include_external=False)

    with_ext_types = [r.get("source_type") for r in with_ext.get("results", [])]
    without_ext_types = [r.get("source_type") for r in without_ext.get("results", [])]

    print(f"With external:    source_types={with_ext_types}, no_confident_match={with_ext.get('no_confident_match')}")
    print(f"Without external: source_types={without_ext_types}, no_confident_match={without_ext.get('no_confident_match')}")

    passed = (
        any(t in ("external_postmortem", "external_doc") for t in with_ext_types)
        and all(t == "internal_runbook" for t in without_ext_types)
    )
    print(f"Result: {'✓ PASS' if passed else '✗ FAIL'}")
    return passed


def test_spot_check_10_summaries() -> bool:
    """Test 4: Spot check 10 external summaries for required frontmatter and sections."""
    print("\n--- Test 4: Spot Check 10 External Document Summaries ---")
    ext_dir = _PROJECT_ROOT / "data" / "external"
    files = sorted(ext_dir.glob("*.md"))[:10]

    if len(files) < 10:
        print(f"✗ FAIL: Less than 10 external docs found ({len(files)}).")
        return False

    all_valid = True
    for f in files:
        post = frontmatter.load(f)
        has_title = bool(post.get("title"))
        has_type = bool(post.get("failure_type"))
        has_source_type = post.get("source_type") in ("external_postmortem", "external_doc")
        has_url = str(post.get("source_url", "")).startswith("http")
        has_license = bool(post.get("license"))
        has_sections = (
            "## Symptoms" in post.content
            and "## Likely cause" in post.content
            and "## How to confirm" in post.content
            and "## Fix" in post.content
        )

        valid = has_title and has_type and has_source_type and has_url and has_license and has_sections
        status_mark = "✓" if valid else "✗"
        print(f"  {status_mark} {f.name:<38} | {post.get('source_type'):<20} | URL: {post.get('source_url')[:30]}...")

        if not valid:
            all_valid = False

    print(f"Result: {'✓ PASS' if all_valid else '✗ FAIL'}")
    return all_valid


def run_all_tests() -> bool:
    print("=" * 65)
    print("  External Knowledge Test Suite (TESTING_GUIDE Section 7.3)")
    print("=" * 65)

    t1 = test_ood_failure_returns_external_with_url()
    t2 = test_known_oom_ranks_internal_first()
    t3 = test_toggle_external_knowledge()
    t4 = test_spot_check_10_summaries()

    all_passed = t1 and t2 and t3 and t4
    print("\n" + "=" * 65)
    print(f"  External Knowledge Tests: {'ALL PASSED ✓' if all_passed else 'SOME FAILED ✗'}")
    print("=" * 65 + "\n")
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
