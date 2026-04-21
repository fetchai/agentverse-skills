---
name: agentverse-manage
description: >
  Manage hosted agents on Fetch.ai's Agentverse: list, start, stop, view logs,
  and delete agents. Provides operational control over your deployed agents.
  Requires AGENTVERSE_API_KEY env var. Use when asked to list agents, check
  agent status, view logs, start/stop agents, or clean up.
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-04-20"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---

# Agentverse Manage

## Overview

Manage your hosted agents on Agentverse. List all agents, start/stop them, read their logs, and delete agents you no longer need.

## When to Use

- User asks "list my agents" or "what agents do I have"
- User asks to "start/stop/restart" an agent
- User asks to "show agent logs" or "what is my agent doing"
- User asks to "delete" or "remove" an agent
- You need to check agent status after deploying

## Prerequisites

- `AGENTVERSE_API_KEY` environment variable set
- Python 3.8+ with `requests`

## Quick Steps

### List all agents
```bash
python3 scripts/manage_agents.py list
```

### Start an agent
```bash
python3 scripts/manage_agents.py start --agent agent1q...
```

### Stop an agent
```bash
python3 scripts/manage_agents.py stop --agent agent1q...
```

### View logs
```bash
python3 scripts/manage_agents.py logs --agent agent1q...
```

### Delete an agent
```bash
python3 scripts/manage_agents.py delete --agent agent1q...
```

## Output Examples

### List
```json
{
  "status": "success",
  "total": 3,
  "agents": [
    {
      "name": "my-image-relay",
      "address": "agent1q...",
      "running": true,
      "compiled": true,
      "domain": "",
      "wallet_address": "fetch1...",
      "created": "2026-04-20T10:00:00Z",
      "updated": "2026-04-20T15:30:00Z"
    }
  ]
}
```

### Logs
```json
{
  "status": "success",
  "agent": "agent1q...",
  "total_entries": 15,
  "showing": 3,
  "logs": [
    {"timestamp": "2026-04-20T15:30:00Z", "message": "Agent started", "level": "info"},
    {"timestamp": "2026-04-20T15:30:01Z", "message": "Sending message...", "level": "info"},
    {"timestamp": "2026-04-20T15:30:35Z", "message": "RESULT:{...}", "level": "info"}
  ]
}
```

## API Reference

| Action | Method | Endpoint |
|--------|--------|----------|
| List agents | GET | `/v1/hosting/agents` |
| Get agent | GET | `/v1/hosting/agents/{address}` |
| Start | POST | `/v1/hosting/agents/{address}/start` |
| Stop | POST | `/v1/hosting/agents/{address}/stop` |
| Delete | DELETE | `/v1/hosting/agents/{address}` |
| Get logs | GET | `/v1/hosting/agents/{address}/logs/latest` |

## Edge Cases

- **Agent already running**: Starting a running agent is safe (no-op or restarts)
- **Agent already stopped**: Stopping a stopped agent is safe (no-op)
- **Delete running agent**: Stop it first, then delete
- **Empty logs**: Agent hasn't produced output yet, or was just started
