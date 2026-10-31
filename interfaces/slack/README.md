# Slack Bot — ChatOps SRE Agent (Task B11)

Socket Mode Slack bot that exposes the ChatOps SRE agent in your Slack workspace.
No public URL or ngrok needed — everything goes through Slack's Socket Mode WebSocket.

---

## Quick start

### 1. Create a Slack App

1. Go to <https://api.slack.com/apps> → **Create New App** → **From scratch**.
2. Name it `chatops-sre`, pick your workspace.

### 2. Enable Socket Mode

* **Settings → Socket Mode** → toggle **Enable Socket Mode** → **ON**.
* Generate an **App-Level Token** with scope `connections:write`.  
  Copy it — this is your `SLACK_APP_TOKEN` (`xapp-…`).

### 3. Add Bot Scopes

**OAuth & Permissions → Scopes → Bot Token Scopes**, add:

| Scope | Purpose |
|---|---|
| `app_mentions:read` | Receive @mentions |
| `chat:write` | Post messages |
| `commands` | Register slash commands |

### 4. Add Event Subscription

* **Event Subscriptions → Enable Events → ON**.
* **Subscribe to Bot Events** → add `app_mention`.

### 5. Add Slash Command

* **Slash Commands → Create New Command**.
* Command: `/chatops`  
* Short description: `Ask the SRE agent a question`  
* Usage hint: `Why is order-service crashing?`

### 6. Install the App

**OAuth & Permissions → Install to Workspace** → allow.  
Copy the **Bot User OAuth Token** — this is your `SLACK_BOT_TOKEN` (`xoxb-…`).

### 7. Set env vars

Add to your `.env` file (never commit this):

```env
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_APP_TOKEN=xapp-your-token-here
```

### 8. Install dependencies

```bash
pip install -r interfaces/slack/requirements.txt
# or from project root:
pip install slack-bolt slack-sdk
```

### 9. Run the bot

```bash
python interfaces/slack/app.py
```

You should see:
```
⚡️ Bolt app is running! (development, app-level token)
```

---

## Usage

### @mention

```
@chatops-sre Why is order-service returning 500 errors?
```

The bot replies in the thread with:
* 🩺 Diagnosis header with confidence badge
* Root cause explanation
* Failure type + agent latency
* 💡 Suggested fix
* 🔧 Tools used
* 📚 Sources

### Slash command

```
/chatops Why is payment-service OOM-killed?
```

Works in any channel. The bot posts the trigger message + threads the diagnosis below it.

### Multi-turn follow-up

Reply in the same thread — the bot re-runs the agent with the same `thread_id`, which gives Person A's agent its conversation memory.

---

## Architecture

```
User (@mention or /chatops)
  │
  ▼
Slack API (Socket Mode WebSocket)
  │
  ▼
interfaces/slack/app.py
  │  1. ACK immediately (< 3 s)
  │  2. Post "🔍 Investigating..." in thread
  │  3. Spawn background thread
  │
  ▼  (background thread)
agent/api.py  ask(question, thread_id)
  │
  ├─► mcp_servers/prometheus/server.py   get_metrics
  ├─► mcp_servers/kubernetes/server.py   get_pod_status / get_events / get_logs / list_services
  └─► mcp_servers/runbooks/server.py     runbook search
  │
  ▼
Block Kit formatted reply  →  Slack thread
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | ✅ | `xoxb-…` bot token from OAuth page |
| `SLACK_APP_TOKEN` | ✅ | `xapp-…` app-level token (Socket Mode) |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SLACK_BOT_TOKEN not set` | Add tokens to `.env` |
| Bot doesn't respond to @mentions | Check `app_mention` event is subscribed and bot is invited to the channel |
| `agent.api` import warning | Ensure you run from the project root, or that `agent/` exists |
| Timeout after 60 s | Agent or Docker stack is slow — check `docker compose ps` |
