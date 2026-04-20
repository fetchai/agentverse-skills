# Agent Chat Protocol — Deep Dive

## Protocol Identity

- **Name**: Agent Chat Protocol
- **Digest**: `proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62`
- **Framework**: [uAgents](https://github.com/fetchai/uAgents) by Fetch.ai
- **Package**: `uagents_core.contrib.protocols.chat`

## Message Types

### ChatMessage

The primary message container. Contains a list of typed content items.

```python
from uagents_core.contrib.protocols.chat import ChatMessage, TextContent
from datetime import datetime
from uuid import uuid4

message = ChatMessage(
    timestamp=datetime.now(),
    msg_id=uuid4(),
    content=[
        TextContent(type="text", text="Your message here")
    ]
)
```

Fields:
- `timestamp` (datetime): When the message was created
- `msg_id` (UUID): Unique message identifier
- `content` (list): List of content items (TextContent, ResourceContent, etc.)

### ChatAcknowledgement

Sent by the receiving agent to confirm receipt.

```python
from uagents_core.contrib.protocols.chat import ChatAcknowledgement

# Received automatically after sending ChatMessage
# Fields:
#   acknowledged_msg_id: UUID — matches the msg_id of the original message
#   timestamp: datetime
```

## Content Types

### TextContent
```python
TextContent(type="text", text="Hello world")
```
- `type`: Always `"text"`
- `text`: The text content (string)

### ResourceContent
```python
# Received in responses (e.g., images)
# Fields:
#   type: "resource"
#   resource_id: UUID
#   resource: dict with "uri" and "metadata"
```

Example resource dict:
```json
{
  "uri": "https://res.cloudinary.com/fetch-ai/image/upload/...",
  "metadata": {
    "mime_type": "image/png",
    "width": 2048,
    "height": 2048
  }
}
```

### StartSessionContent
```python
StartSessionContent(type="start-session")
```
Signals the start of a conversation session.

### EndSessionContent
```python
EndSessionContent(type="end-session")
```
Signals the end of a conversation session.

## Protocol Registration

To use the Chat Protocol in a hosted agent:

```python
from uagents import Protocol
from uagents_core.contrib.protocols.chat import chat_protocol_spec

protocol = Protocol(spec=chat_protocol_spec)

@protocol.on_message(ChatMessage)
async def handle(ctx, sender, msg):
    # Handle incoming messages
    pass

agent.include(protocol, publish_manifest=True)
```

The `publish_manifest=True` flag advertises the protocol in the almanac, making the agent discoverable via protocol-based search.

## Message Flow

```
Sender                          Receiver
  │                                │
  ├── ChatMessage ────────────────►│
  │                                │
  │◄── ChatAcknowledgement ────────┤  (~1 second)
  │                                │
  │    ... processing ...          │
  │                                │
  │◄── ChatMessage (response) ─────┤  (3-60 seconds)
  │                                │
  ├── ChatAcknowledgement ────────►│
  │                                │
```

## Timing Expectations

| Response Type | Typical Latency |
|--------------|----------------|
| ACK | < 1 second |
| Text response | 2-5 seconds |
| Image generation | 20-45 seconds |
| Complex computation | 30-120 seconds |

## Common Issues

1. **"Unable to determine message model"**: Protocol version mismatch. Ensure both agents use the same `chat_protocol_spec`.

2. **No response after ACK**: Agent may have crashed during processing. Check its logs.

3. **Multiple responses**: Some agents send multiple ChatMessages (e.g., progress updates + final result). Collect all RESULT: entries from logs.
