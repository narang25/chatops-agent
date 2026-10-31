"""
ChatOps SRE Slack Bot — Task B11
Socket Mode bot (no public URL needed).

Required env vars (from .env):
  SLACK_BOT_TOKEN  xoxb-...
  SLACK_APP_TOKEN  xapp-...

Scopes needed on your Slack App:
  app_mentions:read, chat:write, commands
  Event: app_mention
  Socket Mode: enabled

Usage:
  python interfaces/slack/app.py
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Any

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# ---------------------------------------------------------------------------
# Bootstrap: project root on path so we can import agent.api
# ---------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("chatops.slack")

# ---------------------------------------------------------------------------
# Slack app
# ---------------------------------------------------------------------------
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    log.error(
        "SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in .env. "
        "See interfaces/slack/README.md for setup instructions."
    )
    sys.exit(1)

app = App(token=SLACK_BOT_TOKEN)

# ---------------------------------------------------------------------------
# Agent import (graceful degradation if agent not available)
# ---------------------------------------------------------------------------
try:
    from agent.api import ask as agent_ask  # type: ignore

    AGENT_AVAILABLE = True
    log.info("agent.api imported successfully")
except ImportError as exc:
    log.warning("agent.api not importable (%s); running in stub mode", exc)
    AGENT_AVAILABLE = False

    def agent_ask(question: str, thread_id: str | None = None, model_id: str | None = None, **_: Any) -> dict:  # type: ignore
        return {
            "question": question,
            "diagnosis": "⚠️ Agent module not available — running in stub mode.",
            "failure_type": "unknown",
            "confidence": 0.0,
            "tool_trace": [],
            "sources": [],
            "latency_s": 0.0,
            "thread_id": thread_id,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TIMEOUT_S = 60  # seconds before we give up waiting for the agent


def _confidence_emoji(score: float) -> str:
    if score >= 0.8:
        return "🟢"
    if score >= 0.5:
        return "🟡"
    return "🔴"


def _build_blocks(result: dict) -> list[dict]:
    """Convert agent result dict into Slack Block Kit blocks."""
    diagnosis = result.get("diagnosis") or "No diagnosis available."
    failure_type = result.get("failure_type") or "unknown"
    confidence = float(result.get("confidence") or 0.0)
    sources = result.get("sources") or []
    tool_trace = result.get("tool_trace") or []
    latency = result.get("latency_s") or 0.0

    confidence_pct = int(confidence * 100)
    emoji = _confidence_emoji(confidence)

    blocks: list[dict] = [
        # ── Header ──────────────────────────────────────────────────
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🩺 ChatOps SRE Diagnosis  {emoji} {confidence_pct}%",
                "emoji": True,
            },
        },
        # ── Diagnosis ───────────────────────────────────────────────
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Root cause*\n{diagnosis}"},
        },
        # ── Metadata fields ─────────────────────────────────────────
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Failure type*\n`{failure_type}`"},
                {"type": "mrkdwn", "text": f"*Agent latency*\n{latency:.2f}s"},
            ],
        },
    ]

    # ── Suggested fix (from diagnosis heuristic) ─────────────────
    fix_hint = _extract_fix(diagnosis, failure_type)
    if fix_hint:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*💡 Suggested fix*\n{fix_hint}"},
        })

    # ── Tools used ───────────────────────────────────────────────
    if tool_trace:
        tools_str = "  •  ".join(str(t) for t in tool_trace[:6])
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"🔧 *Tools used:* {tools_str}"}],
        })

    # ── Sources ──────────────────────────────────────────────────
    if sources:
        src_lines = "\n".join(f"• {s}" for s in sources[:5])
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"📚 *Sources:*\n{src_lines}"}],
        })

    # ── Divider + follow-up hint ─────────────────────────────────
    blocks += [
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
    ]

    return blocks


_FIX_MAP: dict[str, str] = {
    "oom_killed":           "Increase the container memory limit or fix the memory leak. Check `docker stats` and recent heap dumps.",
    "crash_loop":           "Inspect logs with `docker logs <container>`. Fix the bad env var or missing config that causes the exit.",
    "bad_env":              "Set the correct environment variable and restart the container.",
    "health_check_failure": "Check the `/health` endpoint manually. Verify dependencies (DB, upstream) are reachable.",
    "db_timeout":           "Check Postgres connectivity and query performance. Verify `DATABASE_URL` is correct.",
    "dependency_failure":   "Restart the failing upstream service. Check network/firewall rules between containers.",
    "cpu_saturation":       "Profile CPU usage (`docker stats`, cAdvisor). Consider scaling or rate-limiting the `/burn` endpoint.",
}


def _extract_fix(diagnosis: str, failure_type: str) -> str:
    if failure_type in _FIX_MAP:
        return _FIX_MAP[failure_type]
    diag_lower = diagnosis.lower()
    for key, hint in _FIX_MAP.items():
        if key.replace("_", " ") in diag_lower or key in diag_lower:
            return hint
    return ""


# ---------------------------------------------------------------------------
# Core handler (runs in a background thread to keep Slack ACK fast)
# ---------------------------------------------------------------------------
def _handle_question(
    client: Any,
    channel: str,
    thread_ts: str,
    question: str,
    say_ts: str,
) -> None:
    """Called in a thread; calls the agent and updates Slack."""
    result: dict = {}
    error: str | None = None

    done = threading.Event()

    def _run() -> None:
        nonlocal result, error
        try:
            result = agent_ask(question, thread_id=thread_ts)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        finally:
            done.set()

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    timed_out = not done.wait(timeout=TIMEOUT_S)

    if timed_out or error:
        message = (
            "⏱️ The agent timed out. Please try again in a moment."
            if timed_out
            else f"❌ Agent error: {error}"
        )
        client.chat_update(
            channel=channel,
            ts=say_ts,
            text=message,
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message},
                }
            ],
        )
        return

    blocks = _build_blocks(result)
    diagnosis_text = result.get("diagnosis") or "Diagnosis complete."

    client.chat_update(
        channel=channel,
        ts=say_ts,
        text=diagnosis_text,
        blocks=blocks,
    )
    log.info(
        "Replied in channel=%s thread=%s failure_type=%s confidence=%.2f",
        channel,
        thread_ts,
        result.get("failure_type"),
        result.get("confidence", 0.0),
    )


def _dispatch(client: Any, channel: str, thread_ts: str, question: str) -> None:
    """Post 'Investigating...' immediately, then process in background."""
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


# ---------------------------------------------------------------------------
# Event: app_mention
# ---------------------------------------------------------------------------
@app.event("app_mention")
def handle_mention(event: dict, client: Any, say: Any) -> None:
    """Triggered when someone @mentions the bot."""
    text: str = event.get("text", "")
    channel: str = event["channel"]
    thread_ts: str = event.get("thread_ts") or event["ts"]

    # Strip the bot mention token (<@UXXXXXXX>) from the beginning
    question = text.split(">", 1)[-1].strip() if ">" in text else text.strip()
    if not question:
        question = "What is wrong with the system right now?"

    log.info("app_mention channel=%s thread=%s question=%r", channel, thread_ts, question[:80])
    _dispatch(client, channel, thread_ts, question)


# ---------------------------------------------------------------------------
# Slash command: /chatops
# ---------------------------------------------------------------------------
@app.command("/chatops")
def handle_chatops_command(ack: Any, body: Any, client: Any) -> None:
    """
    /chatops <question>
    Posts the result into the channel as a threaded message.
    """
    ack()  # Must ACK within 3 seconds

    question: str = (body.get("text") or "").strip()
    channel: str = body["channel_id"]
    user: str = body.get("user_id", "")

    if not question:
        client.chat_postMessage(
            channel=channel,
            text="Usage: `/chatops <your question>` — e.g. `/chatops Why is order-service down?`",
        )
        return

    # Post the trigger message first so we have a ts to thread against
    trigger_resp = client.chat_postMessage(
        channel=channel,
        text=f"<@{user}> asked: _{question}_",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<@{user}> asked: _{question}_",
                },
            }
        ],
    )
    thread_ts = trigger_resp["ts"]

    log.info("/chatops channel=%s user=%s question=%r", channel, user, question[:80])
    _dispatch(client, channel, thread_ts, question)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    log.info("Starting ChatOps SRE Slack bot (Socket Mode)…")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
