"""
Continuous Learning Loop: Runbook Draft & Approval (Week 5 -- Task A20).
========================================================================

Enables the ChatOps system to continuously learn from resolved incidents:
  1. Draft: Converts an incident plus engineer-confirmed root cause & fix
     into a standard runbook with `status: draft` in `data/runbooks/drafts/`.
  2. Guard: `rag/ingest.py` automatically skips files with `status: draft`.
  3. Approve: An engineer reviews the draft. When approved, the file is moved
     to `data/runbooks/` with `status: published` and immediately ingested into Chroma.

CLI Commands:
  chatops learn "<incident description>"
  chatops approve "<draft_filename>"
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import frontmatter

from agent.llm import clean_output, get_llm
from rag.ingest import ingest_single_runbook

DRAFTS_DIR = PROJECT_ROOT / "data" / "runbooks" / "drafts"
RUNBOOKS_DIR = PROJECT_ROOT / "data" / "runbooks"

DRAFTS_DIR.mkdir(parents=True, exist_ok=True)


DRAFT_SYSTEM_PROMPT = """\
You are an expert SRE knowledge engineer. Your job is to convert resolved incident \
notes and engineer-confirmed findings into a high-quality SRE runbook draft.

Output MUST start with YAML frontmatter containing:
---
title: "Descriptive Actionable Title"
failure_type: "one of: out_of_memory | bad_config | health_check_failure | db_timeout | dependency_failure | disk_full | cpu_saturation | crash_loop | network_timeout | high_error_rate | other"
service: "payment-service | order-service | inventory-service | any"
severity: "low | medium | high | critical"
status: "draft"
---

Followed by these four standard Markdown sections:
## Symptoms
(Bulleted observable symptoms, error codes, logs, and metric deviations)

## Likely cause
(Technical explanation of why the failure occurred)

## How to confirm
(Exact diagnostic shell/kubectl/curl commands to verify the root cause)

## Fix
(Numbered, step-by-step remediation procedure)
"""


def _slugify(text: str) -> str:
    """Creates a clean filesystem slug from text."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:50] or "incident"


def draft_runbook_from_incident(
    incident_description: str,
    root_cause: str | None = None,
    fix: str | None = None,
    service: str | None = None,
    model_id: str | None = None,
) -> tuple[str, Path]:
    """
    Uses the LLM to draft an SRE runbook from an incident description and resolution.
    Saves the output to `data/runbooks/drafts/<slug>.md` with `status: draft`.
    """
    user_prompt = f"Incident Report:\n{incident_description}\n"
    if root_cause:
        user_prompt += f"\nConfirmed Root Cause:\n{root_cause}\n"
    if fix:
        user_prompt += f"\nVerified Remediation Procedure:\n{fix}\n"
    if service:
        user_prompt += f"\nAffected Service:\n{service}\n"

    try:
        llm = get_llm(model_id=model_id)
        response = llm.invoke([
            {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        content = clean_output(response)
    except Exception:
        # Fallback template if LLM is offline or sandbox blocks network
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target_svc = service or "any"
        content = (
            f"---\n"
            f"title: \"Draft Runbook: {incident_description[:50]}\"\n"
            f"failure_type: \"other\"\n"
            f"service: \"{target_svc}\"\n"
            f"severity: \"medium\"\n"
            f"status: \"draft\"\n"
            f"created_at: \"{ts}\"\n"
            f"---\n\n"
            f"## Symptoms\n- {incident_description}\n\n"
            f"## Likely cause\n{root_cause or 'Under investigation.'}\n\n"
            f"## How to confirm\n`kubectl logs <pod-name>` or inspect service metrics.\n\n"
            f"## Fix\n1. {fix or 'Apply standard recovery procedures.'}\n"
        )

    # Ensure frontmatter status is draft
    if "status:" not in content:
        content = content.replace("---", "---\nstatus: \"draft\"", 1)

    # Extract title for filename
    title_match = re.search(r'title:\s*["\']?([^"\']+)["\']?', content)
    title = title_match.group(1) if title_match else incident_description[:30]
    slug = _slugify(title)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"draft-{slug}-{timestamp}.md"
    file_path = DRAFTS_DIR / filename

    file_path.write_text(content, encoding="utf-8")
    return content, file_path


def approve_draft(draft_filename_or_path: str) -> tuple[Path, int]:
    """
    Approves a draft runbook:
      1. Validates the draft file exists.
      2. Updates frontmatter `status` from 'draft' to 'published'.
      3. Moves the file from `data/runbooks/drafts/` to `data/runbooks/`.
      4. Ingests only that file into Chroma DB so it becomes searchable immediately.

    Returns:
        (destination_path, chunk_count)
    """
    target = Path(draft_filename_or_path)
    if not target.is_absolute():
        if (DRAFTS_DIR / target.name).exists():
            target = DRAFTS_DIR / target.name
        elif (RUNBOOKS_DIR / target.name).exists():
            target = RUNBOOKS_DIR / target.name

    if not target.exists():
        raise FileNotFoundError(f"Draft file not found: {draft_filename_or_path}")

    post = frontmatter.load(target)
    post["status"] = "published"
    post["approved_at"] = datetime.now(timezone.utc).isoformat()

    # Determine destination filename in data/runbooks/
    clean_name = target.name.replace("draft-", "")
    dest_path = RUNBOOKS_DIR / clean_name

    # Write approved content to destination
    dest_path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # Remove original draft
    if target.resolve() != dest_path.resolve() and target.exists():
        target.unlink()

    # Index newly approved runbook into Chroma
    chunks_indexed = ingest_single_runbook(dest_path)
    return dest_path, chunks_indexed
