"""
ChatOps SRE Slack Bot — Tasks B11 & B21.
Socket Mode bot with interactive Block Kit diagnosis and human-in-the-loop remediation approval.

Required env vars:
  SLACK_BOT_TOKEN      xoxb-...
  SLACK_APP_TOKEN      xapp-...
  APPROVER_SLACK_IDS   U12345,U67890 (comma-separated authorized Slack user IDs)

Usage:
  python interfaces/slack/app.py
"""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from typing import Any

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))
load_dotenv(os.path.join(ROOT, ".env.infra"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("chatops.slack")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
APPROVER_SLACK_IDS = [
    uid.strip() for uid in os.environ.get("APPROVER_SLACK_IDS", "").split(",") if uid.strip()
]

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    log.warning(
        "SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set. Running in configuration check mode."
    )

app = App(token=SLACK_BOT_TOKEN)

# ---------------------------------------------------------------------------
# Imports from Agent & Remediation
# ---------------------------------------------------------------------------
try:
    from agent.api import ask as agent_ask  # type: ignore
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False

    def agent_ask(question: str, thread_id: str | None = None, **_: Any) -> dict:
        return {
            "question": question,
            "diagnosis": "Running in fallback mode (agent.api not loaded).",
            "failure_type": "unknown",
            "confidence": 0.5,
            "tool_trace": [],
            "sources": [],
            "latency_s": 0.1,
            "thread_id": thread_id,
        }

from mcp_servers.remediation.server import (
    _PROPOSALS,
    apply_remediation,
    log_audit_event,
    propose_remediation,
)

TIMEOUT_S = 180


def _parse_confidence(raw: Any) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        mapping = {"high": 0.9, "medium": 0.6, "low": 0.3}
        cleaned = raw.strip().lower()
        if cleaned in mapping:
            return mapping[cleaned]
        try:
            return float(cleaned)
        except ValueError:
            return 0.5
    return 0.8


def _confidence_emoji(score: float) -> str:
    if score >= 0.8:
        return "🟢"
    if score >= 0.5:
        return "🟡"
    return "🔴"


def _infer_service(result: dict, default: str) -> str:
    text = f"{result.get('question') or ''} {result.get('diagnosis') or ''}".lower()
    for svc in ("payment-service", "order-service", "inventory-service"):
        if svc in text:
            return svc
    return default


def _derive_remediation_proposal(result: dict) -> dict | None:
    """Analyze agent result and propose safe action if applicable."""
    failure_type = (result.get("failure_type") or "").lower()
    diag = (result.get("diagnosis") or "").lower()

    # Check if the agent already called propose_remediation live during this turn
    for step in reversed(result.get("tool_trace") or []):
        if isinstance(step, dict) and step.get("tool") == "propose_remediation":
            summary = step.get("output_summary", "")
            m = re.search(r'"proposal_id"\s*:\s*"([^"]+)"', summary)
            if m:
                pid = m.group(1)
                if pid in _PROPOSALS and not _PROPOSALS[pid].get("used"):
                    return _PROPOSALS[pid]

    if not failure_type or failure_type in ("unknown", "healthy", "none"):
        return None

    if failure_type == "out_of_memory" or ("oom_killed" in diag and "true" in diag):
        svc = _infer_service(result, "payment-service")
        return propose_remediation(svc, "set_memory_limit", {"memory_mb": 256})
    if failure_type in ("crash_loop", "bad_config"):
        svc = _infer_service(result, "order-service")
        return propose_remediation(svc, "restart_service", {})
    if failure_type in ("high_error_rate", "bad_deploy"):
        svc = _infer_service(result, "order-service")
        return propose_remediation(svc, "rollback_deploy", {})
    return None


def _build_blocks(result: dict) -> list[dict]:
    diagnosis = result.get("diagnosis") or "No diagnosis available."
    failure_type = result.get("failure_type") or "none"
    confidence = _parse_confidence(result.get("confidence"))
    sources = result.get("sources") or []
    tool_trace = result.get("tool_trace") or []
    latency = float(result.get("latency_s") or 0.0)

    confidence_pct = int(confidence * 100)
    emoji = _confidence_emoji(confidence)

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🩺 ChatOps SRE Diagnosis  {emoji} {confidence_pct}%",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Root cause*\n{diagnosis[:2850] + ('…' if len(diagnosis) > 2850 else '')}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Failure type*\n`{failure_type}`"},
                {"type": "mrkdwn", "text": f"*Agent latency*\n{latency:.2f}s"},
            ],
        },
    ]

    # Propose operational fix
    proposal = _derive_remediation_proposal(result)
    if proposal and "proposal_id" in proposal:
        p_id = proposal["proposal_id"]
        changes_str = "\n".join(f"• {c}" for c in proposal.get("dry_run", {}).get("changes", []))
        risk = proposal.get("dry_run", {}).get("risk", "medium").upper()

        blocks.extend([
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*🛠️ Proposed Remediation Action (Dry-Run)*\n"
                        f"*Action:* `{proposal.get('action')}` on *{proposal.get('service')}*\n"
                        f"*Risk Level:* `{risk}`\n"
                        f"*Changes:*\n{changes_str}\n"
                        f"_Requires authorized approval within 5 minutes._"
                    ),
                },
            },
            {
                "type": "actions",
                "block_id": f"remediation_actions_{p_id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Approve & Apply", "emoji": True},
                        "style": "primary",
                        "value": p_id,
                        "action_id": "approve_remediation_button",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Reject", "emoji": True},
                        "style": "danger",
                        "value": p_id,
                        "action_id": "reject_remediation_button",
                    },
                ],
            },
        ])

    if tool_trace:
        tool_names = [t.get("tool", str(t)) if isinstance(t, dict) else str(t) for t in tool_trace[:8]]
        tools_str = "  •  ".join(tool_names)
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"🔧 *Tools used:* {tools_str}"}],
        })

    if sources:
        src_lines = "\n".join(f"• {s}" for s in sources[:5])
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"📚 *Sources:*\n{src_lines[:2800]}"}],
        })

    blocks.extend([
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💬 Reply in this thread with follow-up questions.",
                }
            ],
        },
    ])
    return blocks


def _handle_question(client: Any, channel: str, thread_ts: str, question: str, say_ts: str) -> None:
    result: dict = {}
    error: str | None = None
    done = threading.Event()
    use_stub = os.environ.get("AGENT_STUB", "false").lower() == "true"

    def _run() -> None:
        nonlocal result, error
        try:
            result = agent_ask(question, thread_id=thread_ts, stub=use_stub)
        except Exception as exc:
            error = str(exc)
        finally:
            done.set()

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    timed_out = not done.wait(timeout=TIMEOUT_S)

    if timed_out or error:
        message = "⏱️ The agent timed out." if timed_out else f"❌ Agent error: {error}"
        client.chat_update(
            channel=channel,
            ts=say_ts,
            text=message,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": message}}],
        )
        return

    try:
        blocks = _build_blocks(result)
        client.chat_update(
            channel=channel,
            ts=say_ts,
            text=(result.get("diagnosis") or "Diagnosis complete.")[:200],
            blocks=blocks,
        )
    except Exception as exc:
        err_msg = f"❌ Failed to format/post diagnosis: {exc}"
        log.exception("Failed posting Slack diagnosis card")
        client.chat_update(
            channel=channel,
            ts=say_ts,
            text=err_msg,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": err_msg}}],
        )


def _dispatch(client: Any, channel: str, thread_ts: str, question: str) -> None:
    resp = client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text="🔍 Investigating...",
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "🔍 *Investigating…* please wait."},
            }
        ],
    )
    say_ts = resp["ts"]
    threading.Thread(
        target=_handle_question,
        args=(client, channel, thread_ts, question, say_ts),
        daemon=True,
    ).start()


@app.event("app_mention")
def handle_mention(event: dict, client: Any) -> None:
    text: str = event.get("text", "")
    channel: str = event["channel"]
    thread_ts: str = event.get("thread_ts") or event["ts"]
    question = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    if not question:
        question = "What is wrong with the system right now?"
    _dispatch(client, channel, thread_ts, question)


@app.command("/chatops")
def handle_chatops_command(ack: Any, body: Any, client: Any) -> None:
    ack()
    question: str = (body.get("text") or "").strip()
    channel: str = body["channel_id"]
    user: str = body.get("user_id", "")
    if not question:
        client.chat_postMessage(
            channel=channel,
            text="Usage: `/chatops <your question>`",
        )
        return
    trigger_resp = client.chat_postMessage(
        channel=channel,
        text=f"<@{user}> asked: _{question}_",
    )
    _dispatch(client, channel, trigger_resp["ts"], question)


# ---------------------------------------------------------------------------
# Interactive Action Handlers: Approve & Reject (Task B21)
# ---------------------------------------------------------------------------
@app.action("approve_remediation_button")
def handle_approval(ack: Any, body: Any, client: Any) -> None:
    ack()
    user_id = body.get("user", {}).get("id", "")
    user_name = body.get("user", {}).get("username", user_id)
    proposal_id = body.get("actions", [{}])[0].get("value", "")
    channel_id = body.get("channel", {}).get("id", "")
    message_ts = body.get("message", {}).get("ts", "")

    # Approver Authorization Check
    if APPROVER_SLACK_IDS and user_id not in APPROVER_SLACK_IDS:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="🚫 *Authorization Error:* You are not authorized to approve remediation actions.",
        )
        log_audit_event("slack_approval_denied_unauthorized", {"proposal_id": proposal_id, "user_id": user_id})
        return

    record = _PROPOSALS.get(proposal_id)
    if not record:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="⚠️ *Error:* Proposal ID not found or already purged.",
        )
        return

    thread_ts = body.get("message", {}).get("thread_ts") or message_ts

    def _post_verification_update(summary: dict[str, Any]) -> None:
        v_status = summary.get("status", "unknown")
        rolled_back = summary.get("rolled_back", False)
        v_audit = summary.get("audit_id", "")
        v_svc = summary.get("service", "")
        v_reason = summary.get("reason", "")
        if rolled_back or v_status == "worse":
            v_text = (
                f"🔄 *Post-Fix Verification: Rolled Back* on *{v_svc}*\n"
                f"• *Outcome:* Metrics/health degraded ({v_reason}) — previous configuration automatically restored.\n"
                f"• *Audit Reference:* `{v_audit}`"
            )
        elif v_status == "improved":
            v_text = (
                f"✅ *Post-Fix Verification: Improved* on *{v_svc}*\n"
                f"• *Outcome:* Service stable ({v_reason}).\n"
                f"• *Audit Reference:* `{v_audit}`"
            )
        else:
            v_text = (
                f"ℹ️ *Post-Fix Verification: {v_status.title()}* on *{v_svc}*\n"
                f"• *Details:* {v_reason}\n"
                f"• *Audit Reference:* `{v_audit}`"
            )
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=v_text,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": v_text}}],
        )

    token = record.get("token", "")
    result = apply_remediation(
        proposal_id,
        token,
        approver=f"slack:{user_name}",
        on_verify=_post_verification_update,
    )

    if result.get("status") == "applied":
        audit_id = result.get("audit_id")
        action = result.get("action")
        service = result.get("service")
        window_s = result.get("verification_window_seconds", 30)
        status_msg = (
            f"✅ *Remediation Applied Successfully*\n"
            f"• *Action:* `{action}` on *{service}*\n"
            f"• *Approved by:* <@{user_id}>\n"
            f"• *Audit Reference:* `{audit_id}`\n"
            f"• *Verification Window:* {window_s}s (will post result in this thread)"
        )
    else:
        status_msg = f"❌ *Remediation Failed:* {result.get('error', 'Execution error')}"

    # Update original message to remove buttons and show confirmation
    orig_blocks = body.get("message", {}).get("blocks", [])
    updated_blocks = [b for b in orig_blocks if b.get("type") != "actions"]
    updated_blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": status_msg},
    })

    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=status_msg,
        blocks=updated_blocks,
    )


@app.action("reject_remediation_button")
def handle_rejection(ack: Any, body: Any, client: Any) -> None:
    ack()
    user_id = body.get("user", {}).get("id", "")
    proposal_id = body.get("actions", [{}])[0].get("value", "")
    channel_id = body.get("channel", {}).get("id", "")
    message_ts = body.get("message", {}).get("ts", "")

    if proposal_id in _PROPOSALS:
        _PROPOSALS[proposal_id]["status"] = "rejected"
        _PROPOSALS[proposal_id]["used"] = True

    log_audit_event("slack_remediation_rejected", {"proposal_id": proposal_id, "user_id": user_id})

    status_msg = f"❌ *Remediation Rejected by <@{user_id}>*. No changes applied."

    orig_blocks = body.get("message", {}).get("blocks", [])
    updated_blocks = [b for b in orig_blocks if b.get("type") != "actions"]
    updated_blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": status_msg},
    })

    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=status_msg,
        blocks=updated_blocks,
    )


if __name__ == "__main__":
    if SLACK_APP_TOKEN:
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
    else:
        print("SLACK_APP_TOKEN missing. Slack bot cannot start Socket Mode.")
