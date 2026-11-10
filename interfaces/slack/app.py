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

import json
import logging
import os
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
    propose_remediation,
    apply_remediation,
    _PROPOSALS,
    log_audit_event,
)

TIMEOUT_S = 60


def _confidence_emoji(score: float) -> str:
    if score >= 0.8:
        return "🟢"
    if score >= 0.5:
        return "🟡"
    return "🔴"


def _derive_remediation_proposal(result: dict) -> dict | None:
    """Analyze agent result and propose safe action if applicable."""
    failure_type = result.get("failure_type", "").lower()
    diag = (result.get("diagnosis") or "").lower()

    if failure_type == "out_of_memory" or "oom" in diag:
        return propose_remediation("payment-service", "set_memory_limit", {"memory_mb": 256})
    elif failure_type in ["crash_loop", "bad_config"]:
        return propose_remediation("order-service", "restart_service", {})
    elif failure_type in ["high_error_rate", "bad_deploy"]:
        return propose_remediation("order-service", "rollback_deploy", {})
    return None


def _build_blocks(result: dict) -> list[dict]:
    diagnosis = result.get("diagnosis") or "No diagnosis available."
    failure_type = result.get("failure_type") or "unknown"
    confidence = float(result.get("confidence") or 0.0)
    sources = result.get("sources") or []
    tool_trace = result.get("tool_trace") or []
    latency = result.get("latency_s") or 0.0

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
            "text": {"type": "mrkdwn", "text": f"*Root cause*\n{diagnosis}"},
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
        tools_str = "  •  ".join(str(t) for t in tool_trace[:6])
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"🔧 *Tools used:* {tools_str}"}],
        })

    if sources:
        src_lines = "\n".join(f"• {s}" for s in sources[:5])
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"📚 *Sources:*\n{src_lines}"}],
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

    def _run() -> None:
        nonlocal result, error
        try:
            result = agent_ask(question, thread_id=thread_ts)
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

    blocks = _build_blocks(result)
    client.chat_update(
        channel=channel,
        ts=say_ts,
        text=result.get("diagnosis", "Diagnosis complete."),
        blocks=blocks,
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
    question = text.split(">", 1)[-1].strip() if ">" in text else text.strip()
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

    token = record.get("token", "")
    result = apply_remediation(proposal_id, token, approver=f"slack:{user_name}")

    if result.get("status") == "applied":
        audit_id = result.get("audit_id")
        action = result.get("action")
        service = result.get("service")
        status_msg = (
            f"✅ *Remediation Applied Successfully*\n"
            f"• *Action:* `{action}` on *{service}*\n"
            f"• *Approved by:* <@{user_id}>\n"
            f"• *Audit Reference:* `{audit_id}`\n"
            f"• *Verification Window:* 3 minutes"
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
