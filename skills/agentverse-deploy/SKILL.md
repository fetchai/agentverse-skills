---
name: agentverse-deploy
description: >
  Deploy Python code as a hosted agent on Fetch.ai's Agentverse.
  Creates a new agent, uploads code, and optionally starts it.
  Handles the tricky code upload format automatically.
  Requires AGENTVERSE_API_KEY env var. Use when asked to deploy,
  host, or publish an agent on Agentverse.
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-04-20"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---

# Agentverse Deploy

## Overview

Deploy Python code as a hosted agent on Agentverse. The agent runs on Fetch.ai's infrastructure — no server needed. Creates the agent, uploads code in the correct format, and optionally starts it.

## When to Use

- User asks to "deploy this as an agent on Agentverse"
- User asks to "host this code on Agentverse"
- User asks to "create a new hosted agent"
- User has Python agent code they want to run on Agentverse

## Prerequisites

- `AGENTVERSE_API_KEY` environment variable set
- Python 3.8+ with `requests`

## Quick Steps

### 1. Deploy from a file
```bash
python3 scripts/deploy_agent.py --name "my-agent" --file ./my_agent_code.py --start
```

### 2. Deploy inline code
```bash
python3 scripts/deploy_agent.py --name "hello-agent" --code '
@agent.on_event("startup")
async def hello(ctx):
    ctx.logger.info("Hello from my agent!")
'
```

### 3. Parse the result
```json
{
  "status": "success",
  "name": "my-agent",
  "address": "agent1q...",
  "running": true
}
```

## Critical: Hosted Agent Code Rules

Your code MUST follow these rules for the hosted environment:

1. **DO NOT** create an `Agent()` instance — `agent` is pre-created by the platform
2. **DO NOT** call `agent.run()` — the platform manages the lifecycle
3. **DO** use `@agent.on_event("startup")` for initialization
4. **DO** use `ctx.logger.info()` for output (no print/stdout)
5. **DO** use `Protocol` objects and `agent.include()` for message handling

### Valid hosted agent template:
```python
from uagents import Context, Protocol

@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Agent started: {ctx.agent.address}")

@agent.on_interval(period=60.0)
async def periodic(ctx: Context):
    ctx.logger.info("Running periodic task...")
```

### With Chat Protocol:
```python
from datetime import datetime
from uuid import uuid4
from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage, ChatAcknowledgement, TextContent, chat_protocol_spec
)

protocol = Protocol(spec=chat_protocol_spec)

@protocol.on_message(ChatMessage)
async def handle(ctx: Context, sender: str, msg: ChatMessage):
    response = ChatMessage(
        timestamp=datetime.now(), msg_id=uuid4(),
        content=[TextContent(type="text", text="Hello! I received your message.")]
    )
    await ctx.send(sender, response)

agent.include(protocol, publish_manifest=True)
```

## Code Upload Format

The API expects a specific format:
```python
import json
files = [{"language": "python", "name": "agent.py", "value": your_code_string}]
payload = {"code": json.dumps(files)}  # code is a JSON STRING of a list
```

The deploy script handles this automatically.

## Edge Cases

- **Name conflicts**: Agent names don't need to be unique — addresses are unique
- **Code errors**: Check logs after starting (`agentverse-manage logs`)
- **Import errors**: Only standard library + `uagents` + `uagents_core` available in hosted env
- **File size**: Keep code under 100KB

## References

- [Agentverse documentation](https://fetch.ai/docs/guides/agentverse)
- [uAgents framework](https://github.com/fetchai/uAgents)
