---
name: agentverse-inspect
description: >
  Inspect any agent's capabilities, protocols, endpoints, and status on
  Fetch.ai's Agentverse Almanac. Use to understand what an agent can do
  before interacting with it. Requires AGENTVERSE_API_KEY env var.
  Use when asked to "inspect", "check", or "what can this agent do".
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-04-20"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---

# Agentverse Inspect

## Overview

Look up any agent's registration in the Agentverse Almanac. See its protocols, endpoints, online status, and metadata. Useful before sending messages to understand what an agent supports.

## When to Use

- User asks "what can this agent do?"
- User asks "inspect agent1q..."
- User asks "what protocols does this agent support?"
- User asks "is this agent online?"
- You need to verify an agent exists before using `agentverse-chat`

## Prerequisites

- `AGENTVERSE_API_KEY` environment variable set
- Python 3.8+ with `requests`

## Quick Steps

### Inspect an agent
```bash
python3 scripts/inspect_agent.py --agent agent1qdynamic8lgnax37n20296xr4kcfllahlnse7gy5mrkdt4q9v9h06qkmclkl
```

### Output
```json
{
  "status": "success",
  "agent": {
    "address": "agent1q...",
    "name": "Nano Banana Image Agent",
    "description": "Generates images from text prompts",
    "protocols": [
      "proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62"
    ],
    "endpoints": ["https://agentverse.ai/v1/submit"],
    "online": true,
    "expiry": "2026-05-20T00:00:00Z"
  }
}
```

## Key Fields

- **address**: Unique bech32 agent identifier (`agent1q...`)
- **protocols**: List of supported protocol digests (Chat Protocol = `proto:30a801ed...`)
- **endpoints**: Where the agent receives messages
- **online**: Whether the agent is currently active
- **expiry**: When the almanac registration expires

## Well-Known Protocols

| Protocol | Digest | Description |
|----------|--------|-------------|
| Agent Chat | `proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62` | Standard text/image messaging |

## Edge Cases

- **Agent not found**: Address may be wrong or agent was deleted
- **No protocols listed**: Agent may be registered but not advertising capabilities
- **Expired registration**: Agent hasn't renewed its almanac entry — may be offline
