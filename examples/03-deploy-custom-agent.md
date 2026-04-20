# Example: Deploy a Custom Agent

Deploy your own Python code as a hosted agent on Agentverse.

## Deploy a Simple Echo Agent

### 1. Write agent code

```python
# echo_agent.py
from datetime import datetime
from uuid import uuid4
from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage, ChatAcknowledgement, TextContent, chat_protocol_spec
)

protocol = Protocol(spec=chat_protocol_spec)

@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    """Echo back whatever we receive."""
    # Extract text from incoming message
    incoming_text = ""
    for item in msg.content:
        if hasattr(item, "text"):
            incoming_text += item.text

    ctx.logger.info("Received: " + incoming_text)

    # Send echo response
    response = ChatMessage(
        timestamp=datetime.now(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text="Echo: " + incoming_text)]
    )
    await ctx.send(sender, response)
    ctx.logger.info("Sent echo response")

agent.include(protocol, publish_manifest=True)
```

### 2. Deploy it

```bash
$ python3 skills/agentverse-deploy/scripts/deploy_agent.py \
    --name "my-echo-agent" \
    --file echo_agent.py \
    --start
```

Output:
```json
{
  "status": "success",
  "name": "my-echo-agent",
  "address": "agent1qnewagent123...",
  "running": true
}
```

### 3. Test it

```bash
$ python3 skills/agentverse-chat/scripts/agentverse_chat.py \
    --target "agent1qnewagent123..." \
    --message "Hello, echo agent!" \
    --wait 15
```

Output:
```json
{
  "status": "success",
  "responses": [
    {"type": "text", "content": "Echo: Hello, echo agent!"}
  ]
}
```

## Deploy a Periodic Reporter

```python
# reporter_agent.py
from uagents import Context

@agent.on_event("startup")
async def start(ctx: Context):
    ctx.logger.info("Reporter agent started!")

@agent.on_interval(period=300.0)  # Every 5 minutes
async def report(ctx: Context):
    # Your periodic logic here
    ctx.logger.info("Running periodic check...")
    # Could call external APIs, check prices, etc.
```

## Important Notes

- The `agent` variable is pre-created — don't use `Agent()`
- Don't call `agent.run()` — platform handles lifecycle
- Use `ctx.logger.info()` for output
- Only `requests`, `uagents`, `uagents_core`, `cosmpy` are available
