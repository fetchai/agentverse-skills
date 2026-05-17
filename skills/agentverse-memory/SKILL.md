---
name: agentverse-memory
description: >
  Give any AI agent persistent, graph-native memory via Agentverse Memory —
  a managed MCP service with 33 JSON-RPC tools covering 4 memory types
  (episodic, semantic/graph, procedural, working) plus shared multi-agent
  memory spaces. Zero LLM at write time (<5ms writes). Free tier includes
  full graph memory. Requires AM_API_KEY env var.
  Use when asked to store memories, recall past events, build a knowledge
  graph, share memory between agents, or retrieve facts about users/tasks.
license: Apache-2.0
compatibility: Python 3.9+, network access, AM_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-05-17"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests) Bash(pip install agentverse-memory)
---

# Agentverse Memory

## Overview

Give any AI agent persistent, graph-native memory. Agentverse Memory is a managed MCP service that exposes **33 JSON-RPC 2.0 tools** for:

| Memory Type | What it stores | Key tools |
|-------------|----------------|-----------|
| **Episodic** | Time-stamped events, observations, conversations | `memory_store_episode`, `memory_query_episodes` |
| **Semantic** | Knowledge graph triples (subject, predicate, object) | `memory_store_fact`, `memory_query_facts` |
| **Graph** | Graph traversal, shortest path (A*) | `memory_traverse_graph`, `memory_find_path` |
| **Procedural** | Goal-directed skill sequences with outcome tracking | `memory_store_procedure`, `memory_execute_procedure_lookup` |
| **Working** | Ephemeral key-value scratchpad (TTL-aware) | `memory_set_working`, `memory_get_working` |
| **Shared** | Multi-agent shared knowledge spaces | `memory_create_space`, `memory_query_space` |

**Key differentiators:**
- 🚀 **<5ms writes** — zero LLM at write time (TF-IDF only)
- 🌐 **Graph memory on free tier** — unlike Mem0 ($249/mo for graph)
- 🐜 **Pheromone-guided retrieval** — stigmergic trails boost frequently-used memories
- ⏱️ **Temporal validity** — every memory has `valid_at`/`invalid_at` for time-travel queries
- 🔗 **MCP-native** — works with Claude, Cursor, Codex, Copilot, Gemini CLI

## When to Use

- Agent needs to **remember things** across conversations/sessions
- Agent needs to **build a knowledge graph** from interactions
- Agent needs to **find connections** between concepts (graph traversal, shortest path)
- Agent needs to **share knowledge** with other agents (shared spaces)
- Agent needs a **scratchpad** for active task state (working memory)
- Agent needs to **recall what it knew at a specific time** (temporal queries)
- Agent needs to **reuse proven workflows** across tasks (procedural memory)

## When NOT to Use

- You want in-process (local) memory → use Python dict / Redis directly
- You only need simple key-value storage with no graph → use `memory_set_working`
- You want vector similarity search only (no graph) → any vector DB works

## Prerequisites

- `AM_API_KEY` environment variable set (prefix: `am_`)
  - Get a free key: `curl -X POST https://am-server-jbneh74b5q-uc.a.run.app/v1/keys -H "Content-Type: application/json" -d '{"agent_id":"my-agent","tier":"explorer"}'`
- Python 3.9+ with `requests`:
  ```bash
  pip install requests
  # Or use the full SDK:
  pip install agentverse-memory
  ```

## Quick Steps

### 1. Get a free API key
```bash
curl -X POST https://am-server-jbneh74b5q-uc.a.run.app/v1/keys \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "my-agent", "tier": "explorer"}'
# → {"api_key": "am_xxxxxxxxxxxxxxxx", "tier": "explorer", "ops_per_month": 10000}

export AM_API_KEY="am_xxxxxxxxxxxxxxxx"
```

### 2. Check service health
```bash
curl https://am-server-jbneh74b5q-uc.a.run.app/health
# → {"service":"am-server","status":"ok","version":"0.1.0"}
```

### 3. Store an episodic memory
```bash
python3 skills/agentverse-memory/scripts/memory_client.py store-episode \
  --agent-id "my-agent" \
  --content "User Alice asked about quantum computing and preferred simple analogies"
```

### 4. Query episodic memories
```bash
python3 skills/agentverse-memory/scripts/memory_client.py query-episodes \
  --agent-id "my-agent" \
  --query "quantum computing preferences" \
  --limit 5
```

### 5. Store a knowledge graph fact
```bash
python3 skills/agentverse-memory/scripts/memory_client.py store-fact \
  --agent-id "my-agent" \
  --subject "Alice" \
  --predicate "prefers_explanation_style" \
  --object "simple analogies"
```

### 6. Find graph path between concepts
```bash
python3 skills/agentverse-memory/scripts/memory_client.py find-path \
  --agent-id "my-agent" \
  --start "Alice" \
  --end "quantum computing"
```

### 7. Working memory scratchpad
```bash
python3 skills/agentverse-memory/scripts/memory_client.py set-working \
  --agent-id "my-agent" \
  --key "current_task" \
  --value '{"task": "write report", "status": "in_progress"}' \
  --ttl 3600
```

### 8. Direct MCP call (curl)
```bash
curl -X POST https://am-server-jbneh74b5q-uc.a.run.app/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AM_API_KEY" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "memory_store_episode",
      "arguments": {
        "agent_id": "my-agent",
        "content": "User prefers dark mode in all interfaces",
        "source": "user"
      }
    }
  }'
```

### 9. Use the Python SDK (recommended)
```python
from agentverse_memory import AgentverseMemoryClient

client = AgentverseMemoryClient(
    api_key="am_xxxxxxxxxxxxxxxx",
    base_url="https://am-server-jbneh74b5q-uc.a.run.app"
)

# Store an episode
ep = client.store_episode(
    agent_id="my-agent",
    content="User Alice asked about quantum computing, prefers simple analogies",
    source="user"
)
print(f"Episode stored: {ep['id']}")

# Query with natural language
results = client.query_episodes(
    agent_id="my-agent",
    query="what did Alice ask about?",
    limit=5
)
for r in results:
    print(f"[{r['score']:.2f}] {r['content']}")

# Knowledge graph: store a fact
fact = client.store_fact(
    agent_id="my-agent",
    subject="Alice",
    predicate="prefers",
    object="simple analogies"
)

# Graph: find path between concepts
path = client.find_path(
    agent_id="my-agent",
    start_concept="Alice",
    end_concept="quantum computing",
    strategy="pheromone"
)

# Working memory: scratchpad
client.set_working(
    agent_id="my-agent",
    key="current_task",
    value={"status": "active", "topic": "quantum"},
    ttl_seconds=3600
)
task = client.get_working(agent_id="my-agent", key="current_task")

# Stats
stats = client.stats(agent_id="my-agent")
print(f"Episodes: {stats['counts']['episodes']}, Facts: {stats['counts']['facts']}")
```

## All 29 MCP Tools

### Episodic Memory (8 tools)
| Tool | Description |
|------|-------------|
| `memory_store_episode` | Store a time-stamped event or observation |
| `memory_query_episodes` | Natural language search (BM25 + HNSW + pheromone) |
| `memory_get_episode` | Retrieve episode by ID |
| `memory_list_episodes` | Paginated list, sorted by recency or pheromone weight |
| `memory_update_episode` | Update content, metadata, or validity window |
| `memory_delete_episode` | Permanently delete (prefer `invalid_at` for audit trail) |
| `memory_search_timeline` | Search within a specific time window |
| `memory_consolidate_episodes` | Merge related episodes into a summary |

### Semantic / Graph Memory (7 tools)
| Tool | Description |
|------|-------------|
| `memory_store_fact` | Store (subject, predicate, object) triple with temporal validity |
| `memory_query_facts` | Natural language fact search with temporal filter |
| `memory_get_fact` | Retrieve fact by ID |
| `memory_update_fact` | Update fact (creates new version, invalidates old) |
| `memory_delete_fact` | Permanently delete fact |
| `memory_traverse_graph` | BFS outward from seed concept (pheromone-weighted) |
| `memory_find_path` | A* pathfinding between two concepts (pheromone / shortest / semantic) |

### Procedural Memory (5 tools)
| Tool | Description |
|------|-------------|
| `memory_store_procedure` | Store a goal-directed step sequence |
| `memory_query_procedures` | Find procedures by goal description |
| `memory_get_procedure` | Retrieve procedure with success/fail stats |
| `memory_update_procedure` | Update steps or record execution outcome |
| `memory_execute_procedure_lookup` | Find + return best procedure for a goal (primary retrieval) |

### Working Memory (4 tools)
| Tool | Description |
|------|-------------|
| `memory_set_working` | Set key-value with optional TTL (<1ms p50) |
| `memory_get_working` | Get value by key |
| `memory_list_working` | List all keys (with prefix filter) |
| `memory_clear_working` | Delete one key, by prefix, or all working memory |

### Shared Memory Spaces (3 tools)
| Tool | Description |
|------|-------------|
| `memory_create_space` | Create a multi-agent shared knowledge space |
| `memory_join_space` | Join an existing space with invite token |
| `memory_query_space` | Query shared facts across all member agents |

### Utility (2 tools)
| Tool | Description |
|------|-------------|
| `memory_health` | Service health check (Redis, storage, palace pool) |
| `memory_stats` | Agent usage stats, counts, rate limit status |

## MCP Protocol Details

**Endpoint:** `POST https://am-server-jbneh74b5q-uc.a.run.app/mcp`

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "memory_store_episode",
    "arguments": { "agent_id": "...", "content": "..." }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{ "type": "text", "text": "{\"id\":\"ep_abc123\",\"created_at\":\"2026-05-13T12:00:00Z\"}" }]
  }
}
```

**Auth:** `X-API-Key: am_xxxxxxxxxxxxxxxx`

**Tools list:** `POST /mcp` with `{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}`

## Pricing

| Tier | Price | Ops/month | Graph A* | Shared Spaces |
|------|-------|-----------|----------|---------------|
| **Explorer** | Free | 10,000 | BFS only | 0 |
| **Builder** | $19/mo | 100,000 | ✅ A* included | 3 spaces |
| **Pro** | $99/mo | Unlimited | ✅ A* included | Unlimited |

Get started free: `POST /v1/keys` with `"tier": "explorer"`

## API Reference

Full API reference: https://agentverse.ai/docs/api  
MCP integration guide: https://agentverse.ai/docs/mcp  
Python SDK docs: https://agentverse.ai/docs/python-sdk

## How It Works

1. **Write path**: Content → TF-IDF keyword extraction → sled embedded store → <5ms
2. **Read path**: Query → BM25 + HNSW vector search → Reciprocal Rank Fusion → pheromone reweighting → results
3. **Graph**: Knowledge triples form an in-memory graph; A* pathfinding uses pheromone edge weights
4. **Pheromone decay**: `w(t) = w₀ × exp(-Δt/τ)` — lazy computation at query time, no background daemon
5. **Shared spaces**: Dedicated storage namespace per space; DID/VC access control for ASI Chain identity

## Edge Cases

- **Rate limits**: 429 response — check `X-RateLimit-Reset` header and retry after reset
- **No API key**: 401 response — set `AM_API_KEY` and ensure it starts with `am_`
- **Tool not found**: 404 on method — verify tool name matches spec (all lowercase, `memory_` prefix)
- **Large content**: Episode content limited to 64KB; facts to 1KB subject/predicate/object
- **Temporal filter**: `valid_at` ISO 8601 string — use `Z` suffix for UTC

## References

- [Agentverse Memory Docs](https://agentverse.ai/docs)
- [API Reference](https://agentverse.ai/docs/api)
- [GitHub: fetchai/agentverse-memory](https://github.com/fetchai/agentverse-memory)
- [Python SDK: agentverse-memory](https://pypi.org/project/agentverse-memory/)
- [npm: @fetchai/agentverse-memory](https://www.npmjs.com/package/@fetchai/agentverse-memory)
- [Agentverse Platform](https://agentverse.ai)
