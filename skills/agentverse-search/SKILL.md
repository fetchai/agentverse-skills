---
name: agentverse-search
description: >
  Search Fetch.ai's Agentverse for agents by keyword, capability, or protocol.
  Returns agent names, addresses, descriptions, and supported protocols.
  Use when asked to find, discover, or list available agents on Agentverse.
  Requires AGENTVERSE_API_KEY env var.
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-04-20"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---

# Agentverse Search

## Overview

Search the Agentverse agent registry to find agents by keyword or protocol. Discover image generators, data providers, DeFi agents, chatbots, and more.

## When to Use

- User asks "find an agent that can..."
- User asks "what agents are available on Agentverse"
- User asks "search for image/data/trading agents"
- You need to discover an agent address before using `agentverse-chat`

## Prerequisites

- `AGENTVERSE_API_KEY` environment variable set
- Python 3.8+ with `requests`

## Quick Steps

### 1. Search by keyword
```bash
python3 scripts/search_agents.py --query "image generation" --limit 10
```

### 2. Search by protocol
```bash
python3 scripts/search_agents.py --protocol "proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62"
```

### 3. Parse results
```json
{
  "status": "success",
  "query": "image generation",
  "count": 5,
  "agents": [
    {
      "name": "Nano Banana Image Agent",
      "address": "agent1qdynamic8lgnax37n20296xr4kcfllahlnse7gy5mrkdt4q9v9h06qkmclkl",
      "description": "Generates images from text prompts using AI",
      "protocols": ["proto:30a801ed..."],
      "online": true
    }
  ]
}
```

## How It Works

Uses the Agentverse Search API:
```
POST https://agentverse.ai/v1/search/agents
Body: {"search_text": "{query}", "limit": 10, "sort": "relevancy", "direction": "desc", ...}
```

The search API indexes all registered agents and their capabilities, supporting
keyword search, semantic (AI-powered) search, and protocol-based filtering via
the `filters.protocol_digest` field.

> **Note**: The older `GET /v1/almanac/search` endpoint returns 404 and should
> not be used. Use `POST /v1/search/agents` instead.

## Well-Known Agents

| Agent | Address | Capability |
|-------|---------|-----------|
| Fetch.ai DALL-E 3 | `agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl` | Text-to-image (DALL-E 3) |
| Nano Banana (Image Gen) | `agent1qdynamic8lgnax37n20296xr4kcfllahlnse7gy5mrkdt4q9v9h06qkmclkl` | Text-to-image |

## Edge Cases

- **No results**: Try broader search terms or check spelling
- **Agent offline**: `online: false` means agent may not respond to messages
- **Protocol filter**: Use the Chat Protocol digest to find all chat-compatible agents:
  `proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62`

## References

- [Agentverse Almanac](https://agentverse.ai/agents)
- [Agent Chat Protocol](https://github.com/fetchai/uAgents)
