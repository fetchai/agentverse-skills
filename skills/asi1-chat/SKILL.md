---
name: asi1-chat
description: >
  Query the ASI:One LLM — the AI model by the ASI Alliance (Fetch.ai +
  SingularityNET + Ocean Protocol). OpenAI-compatible API. Supports
  asi1 and asi1-mini models. Requires ASI_ONE_API_KEY env var.
  Use when asked to "use ASI", "query ASI:One", or "use the Fetch.ai LLM".
license: Apache-2.0
compatibility: Python 3.8+, network access, ASI_ONE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-04-20"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---

# ASI:One Chat

## Overview

Query the ASI:One large language model — built by the Artificial Superintelligence (ASI) Alliance. OpenAI-compatible API with `asi1` (full) and `asi1-mini` (fast) models.

## When to Use

- User asks to "use ASI:One" or "query the ASI LLM"
- User asks to "use Fetch.ai's AI model"
- User wants an alternative to OpenAI/Anthropic for a specific query
- User asks about ASI Alliance AI capabilities

## Prerequisites

- `ASI_ONE_API_KEY` environment variable set
  - Get one at: https://asi1.ai (sign up → API keys)
- Python 3.8+ with `requests`

## Quick Steps

### 1. Simple query
```bash
python3 scripts/asi1_chat.py --prompt "Explain the ASI Alliance in 3 sentences"
```

### 2. With system prompt
```bash
python3 scripts/asi1_chat.py \
  --prompt "What are the benefits of decentralized AI?" \
  --system "You are a blockchain and AI expert. Be concise." \
  --model asi1-mini
```

### 3. Streaming mode
```bash
python3 scripts/asi1_chat.py --prompt "Write a haiku about AI agents" --stream
```

### 4. Output
```json
{
  "status": "success",
  "model": "asi1-mini",
  "response": "The ASI Alliance is a collaboration between Fetch.ai, SingularityNET, and Ocean Protocol...",
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 87,
    "total_tokens": 99
  }
}
```

## API Details

- **Base URL**: `https://api.asi1.ai/v1`
- **Endpoint**: `/chat/completions`
- **Models**: `asi1` (powerful), `asi1-mini` (fast, cheaper)
- **Format**: OpenAI-compatible (same request/response format)
- **Auth**: `Authorization: Bearer {ASI_ONE_API_KEY}`

## Also Works with OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["ASI_ONE_API_KEY"],
    base_url="https://api.asi1.ai/v1"
)

response = client.chat.completions.create(
    model="asi1-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Edge Cases

- **Rate limits**: If 429 error, wait and retry
- **Timeout**: Large prompts may take 30s+ — use `asi1-mini` for speed
- **Streaming**: Use `--stream` for real-time output on long responses
- **Token limits**: Context window varies by model — keep prompts reasonable

## About ASI:One

ASI:One is the AI model from the [ASI Alliance](https://asi.ai) — a merger of:
- **Fetch.ai** — Autonomous AI agents and infrastructure
- **SingularityNET** — Decentralized AI marketplace
- **Ocean Protocol** — Data exchange and monetization

The ASI token (formerly FET) is the native token of the ecosystem.
