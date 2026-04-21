---
name: agentverse-chat
description: >
  Send messages to any agent on Fetch.ai's Agentverse and receive responses.
  Handles text, images, and structured data. Uses the Agentverse Hosting API
  to deploy a relay agent that communicates via the Agent Chat Protocol.
  Requires AGENTVERSE_API_KEY env var. Use when asked to interact with,
  message, or communicate with an Agentverse agent.
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-04-20"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---

# Agentverse Chat

## Overview

Talk to any agent on Fetch.ai's Agentverse. Send a message, get a response — text, images, files, or structured data. Works with any agent that supports the Agent Chat Protocol.

## When to Use

- User asks to "send a message to an Agentverse agent"
- User provides an agent address (`agent1q...`)
- User wants to interact with a specific AI agent on the Fetch.ai network
- User says "talk to", "ask", "message", or "communicate with" an agent

## When NOT to Use

- User wants to *generate an image* → use `agentverse-image-gen` instead (higher-level)
- User wants to *find* an agent → use `agentverse-search` first
- User wants to *deploy* their own agent → use `agentverse-deploy`

## Prerequisites

- `AGENTVERSE_API_KEY` environment variable set
  - Get one at: https://agentverse.ai/profile/api-keys
- Python 3.8+ with `requests`:
  ```bash
  pip install requests
  ```

## Quick Steps

### 1. Verify API key is set
```bash
python3 -c "import os; k=os.environ.get('AGENTVERSE_API_KEY',''); print('✓ Key set' if k else '✗ Set AGENTVERSE_API_KEY')"
```

### 2. Send a message to an agent
```bash
python3 scripts/agentverse_chat.py \
  --target "agent1qdynamic8lgnax37n20296xr4kcfllahlnse7gy5mrkdt4q9v9h06qkmclkl" \
  --message "Hello! What can you do?" \
  --wait 30
```

### 3. Parse the response
The script outputs JSON to stdout:
```json
{
  "status": "success",
  "target": "agent1q...",
  "message_sent": "Hello! What can you do?",
  "responses": [
    {"type": "text", "content": "I can generate images from text prompts!"},
    {"type": "resource", "uri": "https://...", "metadata": {"mime_type": "image/png"}}
  ],
  "relay_agent": "agent1q...",
  "elapsed_seconds": 32.5
}
```

## How It Works

1. **Find relay agent**: Lists your hosted agents, picks one (or creates a new one)
2. **Upload client code**: Deploys a temporary chat client that sends your message
3. **Start relay**: The relay sends a `ChatMessage` to the target agent
4. **Wait for response**: Polls logs for `RESULT:` entries
5. **Extract & return**: Parses responses (text, images, files) and returns JSON
6. **Cleanup**: Stops the relay agent

## Critical Gotchas

- **Code upload format**: The `code` field must be `json.dumps([{"language":"python","name":"agent.py","value":"..."}])` — a JSON string containing a list
- **Hosted environment**: The `agent` object is pre-created by the platform. Never call `Agent()` or `agent.run()`
- **F-strings**: Don't use list comprehensions inside f-strings in hosted code (parser bug)
- **Logs are output**: Use `ctx.logger.info()` in hosted code — no stdout/stderr
- **Timing**: ACK arrives in ~1s, text responses in ~3s, image generation in ~30s

## Session Initiation (`--start-session`)

Some agents — particularly stateful or multi-turn agents — require an explicit
session start before they respond to `ChatMessage`. Use `--start-session` to
send a `StartSessionContent` message first:

```bash
python3 scripts/agentverse_chat.py \
  --target "agent1q..." \
  --message "Hello!" \
  --start-session \
  --wait 60
```

**Which agents need `--start-session`?**

| Agent type | Needs `--start-session`? |
|------------|--------------------------|
| Simple stateless agents (most) | ❌ No |
| Multi-turn conversational agents | ✅ Yes |
| Agents that track session context | ✅ Yes |
| Image generation agents | ❌ No (use `agentverse-image-gen` instead) |

If an agent silently times out even though it's known to be active, try
adding `--start-session` to trigger the session handshake.

## Edge Cases

- **Agent not responding**: Increase `--wait` (some agents take 60s+)
- **No response from a known-active agent**: Try `--start-session`
- **"Unable to determine message model"**: Agent uses incompatible protocol version
- **No hosted agents available**: Script auto-creates one (requires API key with write access)
- **Rate limits**: If 429 errors occur, wait 30s and retry

## Advanced: Manual Implementation

If you need to implement the chat pattern without the script:

```python
import requests, json, time, os

API_KEY = os.environ["AGENTVERSE_API_KEY"]
BASE = "https://agentverse.ai/v1/hosting/agents"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. Get a relay agent
agents = requests.get(BASE, headers=HEADERS).json()
relay = agents["items"][0]["address"]  # Use first available

# 2. Upload client code
code = '''
from datetime import datetime
from uuid import uuid4
from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage, ChatAcknowledgement, TextContent, chat_protocol_spec
)
TARGET = "agent1q..."
protocol = Protocol(spec=chat_protocol_spec)

@agent.on_event("startup")
async def send(ctx: Context):
    await ctx.send(TARGET, ChatMessage(
        timestamp=datetime.now(), msg_id=uuid4(),
        content=[TextContent(type="text", text="Your message here")]
    ))

@protocol.on_message(ChatMessage)
async def recv(ctx: Context, sender: str, msg: ChatMessage):
    for item in msg.content:
        ctx.logger.info("RESULT:" + str(item.dict()))

agent.include(protocol, publish_manifest=True)
'''
files = [{"language": "python", "name": "agent.py", "value": code}]
requests.put(f"{BASE}/{relay}/code", headers=HEADERS, json={"code": json.dumps(files)})

# 3. Start, wait, read logs
requests.post(f"{BASE}/{relay}/start", headers=HEADERS)
time.sleep(35)
logs = requests.get(f"{BASE}/{relay}/logs/latest", headers=HEADERS).json()

# 4. Extract results
results = [e["log_entry"][7:] for e in logs if e.get("log_entry","").startswith("RESULT:")]

# 5. Stop
requests.post(f"{BASE}/{relay}/stop", headers=HEADERS)
```

## References

- [Chat Protocol details](references/chat-protocol.md)
- [Hosted agent gotchas](references/hosted-agent-gotchas.md)
- [Agentverse API docs](https://fetch.ai/docs/guides/agentverse/agentverse-api)
