---
name: agentverse-memory
description: >
  Give any AI agent persistent, graph-native memory via Agentverse Memory —
  a managed MCP service with 35 JSON-RPC tools covering 4 memory types
  (episodic, semantic/graph, procedural, working) plus shared multi-agent
  memory spaces. Zero LLM at write time (<5ms writes, $0 ingest). Graph memory
  on every tier — including free. Hybrid retrieval (TF-IDF + dense, RRF-fused).
  Requires AM_API_KEY env var.
  Use when asked to store memories, recall past events, build a knowledge
  graph, share memory between agents, or retrieve facts about users/tasks.
license: Apache-2.0
compatibility: Python 3.9+, network access, AM_API_KEY env var
metadata:
  version: "1.3.0"
  author: "Fetch.ai"
  last-updated: "2026-06-26"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(mem *) Bash(pip install requests)
---

# Agentverse Memory

## Overview

Give any AI agent persistent, graph-native memory. Agentverse Memory is a managed MCP service that exposes **35 JSON-RPC 2.0 tools** for:

| Memory Type | What it stores | Key tools |
|-------------|----------------|-----------|
| **Episodic** | Time-stamped events, observations, conversations | `memory_store_episode`, `memory_search_episodes` |
| **Entity** | Named entities with typed properties | `memory_store_entity`, `memory_get_entity` |
| **Graph** | Knowledge graph triples, traversal, pathfinding | `memory_traverse_graph`, `memory_find_path` |
| **Procedural** | Goal-directed skill sequences with outcome tracking | `memory_store_procedure`, `memory_match_procedure` |
| **Working** | Ephemeral key-value scratchpad (TTL-aware) | `memory_set_working`, `memory_get_working` |
| **Shared** | Multi-agent shared knowledge spaces | `memory_create_shared_space`, `memory_shared_query` |
| **Pheromone** | Stigmergic trails on memory paths | `memory_deposit_pheromone`, `memory_get_pheromone` |

**Key differentiators:**
- 🚀 **<5ms writes, $0 ingest** — zero LLM inference at write time. Embeddings are computed lazily on the *read* path and cached per agent, so ingestion never pays an LLM/embedding bill. This is the core cost moat.
- 🌐 **Graph memory on every tier — including free.** Knowledge triples, BFS graph traversal, and all 4 memory types are available on the free Explorer tier (most vector-only free tiers don't include graph at all).
- 🔀 **Hybrid retrieval by default** — lexical (TF-IDF) and dense (`text-embedding-3-small`) candidate sets fused via Reciprocal Rank Fusion (RRF, k=60). Live default-on in production.
- 🐜 **Pheromone-guided retrieval (opt-in)** — stigmergic trails that boost frequently-recalled memories. Best for warm-cache / repeated-access and multi-agent shared workloads; off by default for single-pass queries.
- 🔗 **MCP-native** — 35 tools over JSON-RPC; works with Claude, Cursor, Codex, Copilot, Gemini CLI.

> **Positioning (honest):** Agentverse Memory competes on **total cost of ownership** ($0 write-time inference), **graph at every tier**, **native MCP**, and **multi-agent pheromone transfer** — not on a claim of higher raw retrieval accuracy than other systems. Keep the headline on cost and capabilities.

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
  - Get a free key (real response shape shown below):
    ```bash
    curl -X POST https://am-server-jbneh74b5q-uc.a.run.app/v1/keys \
      -H "Content-Type: application/json" \
      -d '{"agent_id":"my-agent","tier":"explorer"}'
    # → {"agent_id":"my-agent","key":"am_xxxxxxxx","key_id":"...",
    #    "monthly_op_limit":50000,"tier":"explorer","warning":"Store this key securely..."}
    ```
    The field is **`key`** (not `api_key`) and the limit is **`monthly_op_limit`** (not `ops_per_month`).
- Python 3.9+ with `requests`:
  ```bash
  pip install requests
  ```

> **Onboarding paths that work today:**
> 1. The bundled **`scripts/memory_client.py`** CLI (recommended — covers the common operations).
> 2. **Raw curl / MCP** calls to `…/mcp` (works from any language).
>
> A first-party **Python / TypeScript SDK is coming soon** (pending package publish). The PyPI/npm packages are *not yet live*, so don't rely on `pip install agentverse-memory` / `npm install @fetchai/agentverse-memory` yet — use the bundled script or raw MCP for now.

## Quick Steps

### 1. Get a free API key
```bash
curl -X POST https://am-server-jbneh74b5q-uc.a.run.app/v1/keys \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "my-agent", "tier": "explorer"}'
# → {"agent_id":"my-agent","key":"am_xxxxxxxxxxxxxxxx","key_id":"...",
#    "monthly_op_limit": 50000, "tier": "explorer", "warning": "..."}

# Export the value of the "key" field:
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

### 4. Query episodic memories (hybrid retrieval)
```bash
python3 skills/agentverse-memory/scripts/memory_client.py query-episodes \
  --agent-id "my-agent" \
  --query "quantum computing preferences" \
  --limit 5
# Result includes "retrieval":"hybrid" (TF-IDF ∪ dense, RRF-fused).
# Add --no-hybrid to force lexical-only, or --use-pheromone for warm-cache re-ranking.
```

### 5. Store a knowledge graph fact
```bash
python3 skills/agentverse-memory/scripts/memory_client.py store-fact \
  --agent-id "my-agent" \
  --subject "Alice" \
  --predicate "prefers_explanation_style" \
  --object "simple analogies"
```

### 6. Find graph path between concepts (Builder+ tier)
```bash
python3 skills/agentverse-memory/scripts/memory_client.py find-path \
  --agent-id "my-agent" \
  --start "Alice" \
  --end "quantum computing"
# A* pathfinding requires the Builder tier or above. On the free Explorer tier
# use traverse-graph (BFS), which is available everywhere.
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

> ⚠️ **Onboarding gotcha:** JSON-RPC must be POSTed to the **`/mcp`** path, not the base URL. POSTing to the base URL returns an actionable error (it will not silently succeed). Always set your endpoint to `…/mcp`.

### 8b. Bash CLI (`mem`) — optional, shell-first workflows

For shell-first workflows there is a small `mem` CLI (built around `curl` + `jq`)
distributed with the Agentverse Memory service. It wraps the same `/mcp` endpoint:

```bash
export AM_BASE_URL="https://am-server-jbneh74b5q-uc.a.run.app"   # MEM_URL is derived as $AM_BASE_URL/mcp
export AM_API_KEY="am_xxxxxxxxxxxxxxxx"

mem doctor                                            # validate the onboarding chain
mem episode "User prefers dark mode" '{"tags":["pref"]}'
mem search "dark mode"
mem stats
```

`mem doctor` checks env → `/mcp` → auth → a metadata round-trip → the usage
meter and prints a PASS/FAIL checklist. If you don't have the `mem` CLI installed,
the bundled `scripts/memory_client.py` (above) covers the same operations and works
out of the box with only `requests`.

### 9. Python / TypeScript SDK (coming soon)

A first-party SDK is in progress:

```text
# NOT YET PUBLISHED — do not use yet:
#   pip install agentverse-memory          (PyPI package not live)
#   npm install @fetchai/agentverse-memory (npm package not live)
```

Until the packages are published, use `scripts/memory_client.py` or call the
`/mcp` endpoint directly (any language with an HTTP client works — it's plain
JSON-RPC 2.0). Track SDK status at the docs site linked under
[API Reference](#api-reference).

## All 35 MCP Tools

### Episodic Memory (5 tools)
| Tool | Description |
|------|-------------|
| `memory_store_episode` | Store a time-stamped event or observation |
| `memory_get_episodes` | Retrieve episodes by agent, with pagination |
| `memory_search_episodes` | Natural-language search — **hybrid retrieval** (TF-IDF ∪ dense embeddings, RRF-fused) |
| `memory_search_timeline` | Search within a specific time window |
| `memory_consolidate_episodes` | Merge related episodes into a summary |

### Entity Memory (5 tools)
| Tool | Description |
|------|-------------|
| `memory_store_entity` | Store a named entity with typed properties |
| `memory_get_entity` | Retrieve entity by name or ID |
| `memory_list_entities` | List entities with prefix/type filter |
| `memory_store_relation` | Store a typed relationship between two entities (by entity ID) |
| `memory_get_relations` | Get all relations for an entity |

### Graph Operations (5 tools)
| Tool | Description |
|------|-------------|
| `memory_query_graph` | Keyword graph query over stored triples |
| `memory_semantic_search` | Vector similarity search across memory types |
| `memory_get_neighbors` | Get direct neighbors of a graph node |
| `memory_find_path` | A* pathfinding between concepts (pheromone/shortest/semantic) — **Builder+ tier** |
| `memory_traverse_graph` | BFS outward from a start node (free on every tier) |

### Graph Direct (3 tools)
| Tool | Description |
|------|-------------|
| `memory_graph_add_triple` | Add a (subject, predicate, object) triple directly |
| `memory_graph_neighbors` | Get low-level graph neighbors of a node |
| `memory_graph_shortest_path` | Shortest path between two nodes |

### Procedural Memory (4 tools)
| Tool | Description |
|------|-------------|
| `memory_store_procedure` | Store a named, goal-directed step sequence |
| `memory_get_procedure` | Retrieve procedure with success/fail stats |
| `memory_match_procedure` | Find the best procedure for a task description |
| `memory_update_procedure` | Update steps or record execution outcome |

### Working Memory (4 tools)
| Tool | Description |
|------|-------------|
| `memory_set_working` | Set key-value with optional TTL (<1ms p50) |
| `memory_get_working` | Get value by key |
| `memory_list_working` | List all keys (with prefix filter) |
| `memory_clear_working` | Delete one key, by prefix, or all |

### Pheromone (2 tools)
| Tool | Description |
|------|-------------|
| `memory_deposit_pheromone` | Deposit a pheromone trail on a memory path |
| `memory_get_pheromone` | Get the current pheromone weight for a path |

### Shared Memory Spaces (5 tools)
| Tool | Description |
|------|-------------|
| `memory_create_shared_space` | Create a multi-agent shared knowledge space |
| `memory_join_shared_space` | Join a space by `space_id` (your JWT must grant access — see [Shared Spaces & JWT Authentication](#shared-spaces--jwt-authentication)) |
| `memory_shared_store_entity` | Store an entity in a shared space |
| `memory_shared_query` | Query cross-agent memory within a shared space |
| `memory_list_shared_spaces` | List shared spaces the agent belongs to |

### Utility (2 tools)
| Tool | Description |
|------|-------------|
| `memory_get_stats` | Agent usage stats, counts, rate-limit status |
| `memory_delete_agent` | Delete all memory for an agent (irreversible) |

### `memory_search_episodes` parameters

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `query` | string | — | Required search text |
| `limit` | integer | 12 | Max evidence items to return |
| `use_hybrid` | boolean | `true` | Fuse the TF-IDF candidate set with dense embeddings (RRF). Set `false` for lexical-only. |
| `use_pheromone` | boolean | `false` | Re-rank by pheromone weight. Best for warm/repeated-access workloads; off by default. |
| `max_content_chars` | integer | — | Optional: trim each result's content to N chars to save tokens |

The result reports the retrieval mode used as `"retrieval": "hybrid"` or `"retrieval": "tfidf"`.

## Tool Parameter Reference (all 35 tools)

Complete parameters for every tool, grouped by memory type. Each tool's arguments
go inside the JSON-RPC `params.arguments` object (see [Direct MCP call](#8-direct-mcp-call-curl)).
The five tools that publish a live `inputSchema` via `tools/list`
(`memory_store_episode`, `memory_search_episodes`, `memory_set_working`,
`memory_graph_neighbors`, `memory_graph_shortest_path`) match the tables below;
this section documents the remaining tools that don't yet advertise a schema.

> **Conventions**
> - **`agent_id` is *not* a tool argument.** Your identity — and which memory palace you read/write — is derived from the `AM_API_KEY` you authenticate with. (The `--agent-id` flag in `memory_client.py` is a client-side convenience; the server ignores any `agent_id` passed in `arguments`.)
> - `✅` = required · `—` = optional / not applicable · timestamps are **RFC3339** strings (use a `Z` suffix for UTC).
> - Shared-space tools additionally require **JWT auth** (`Authorization: Bearer <jwt>`), not just an API key.

### Episodic Memory

| Tool | Parameter | Type | Req | Default | Description |
|------|-----------|------|:---:|---------|-------------|
| `memory_store_episode` | `content` | string | ✅ | — | Episode text content |
| | `metadata` | object | — | — | Structured metadata (chunk provenance merged in when content is split) |
| | `valid_at` | string | — | now | Validity timestamp (RFC3339) |
| | `chunk` | boolean | — | auto | Force (`true`) / disable (`false`) chunking; auto = chunk only when content > `chunk_threshold` |
| | `chunk_threshold` | integer | — | 6000 | Auto-chunk content longer than this many chars |
| | `chunk_size` | integer | — | 2800 | Target chunk size (chars) |
| | `chunk_overlap` | integer | — | 450 | Overlap between consecutive chunks (chars) |
| `memory_get_episodes` | `limit` | integer | — | 10 | Max episodes to return (most recent first) |
| `memory_search_episodes` | `query` | string | ✅ | — | Search text — full detail in the [table above](#memory_search_episodes-parameters) |
| | `limit` | integer | — | 12 | Max evidence items to return |
| | `use_hybrid` | boolean | — | server default (**ON** in prod) | Fuse TF-IDF ∪ dense embeddings (RRF) |
| | `use_pheromone` | boolean | — | server default (**OFF** in prod) | Re-rank by pheromone weight |
| | `max_content_chars` | integer | — | no trim | Trim each result's content to N chars |
| `memory_search_timeline` | `start_time` | string | ✅ | — | Window start (RFC3339) |
| | `end_time` | string | ✅ | — | Window end (RFC3339) |
| `memory_consolidate_episodes` | `before_time` | string | — | 7 days ago | Consolidate episodes older than this (RFC3339); those with pheromone weight < 0.1 are soft-deleted |

### Entity Memory

| Tool | Parameter | Type | Req | Default | Description |
|------|-----------|------|:---:|---------|-------------|
| `memory_store_entity` | `entity_id` | string | ✅ | — | Unique entity identifier / name |
| | `type` | string | — | `"concept"` | Entity type |
| | `description` | string | — | — | Human-readable description |
| | `predicate` | string | — | — | Predicate (for subject-predicate-object facts) |
| | `object_value` | string | — | — | Object value (for subject-predicate-object facts) |
| | `properties` | object | — | — | Structured metadata (alias of `metadata`) |
| | `metadata` | object | — | — | Structured metadata (takes precedence if both are sent) |
| `memory_get_entity` | `entity_id` | string | ✅ | — | Entity id/name to fetch (returns `found:false` if absent) |
| `memory_list_entities` | `limit` | integer | — | 20 | Max entities to return |
| `memory_store_relation` | `from_id` | string | ✅ | — | Source entity (UUID **or** name; a new name is auto-created as a stub) |
| | `to_id` | string | ✅ | — | Target entity (UUID **or** name; auto-created if new) |
| | `predicate` | string | ✅ | — | Relation label |
| | `weight` | number | — | 1.0 | Edge weight |
| `memory_get_relations` | `entity_id` | string | ✅ | — | Entity id/name whose relations to fetch |

### Graph Operations

| Tool | Parameter | Type | Req | Default | Description |
|------|-----------|------|:---:|---------|-------------|
| `memory_query_graph` | `query` | string | ✅ | — | Keyword graph query text |
| `memory_semantic_search` | `query` | string | ✅ | — | Search text (TF-IDF over entities) |
| | `limit` | integer | — | 10 | Max results |
| `memory_get_neighbors` | `entity_id` | string | ✅ | — | Entity id/name to expand from |
| | `hops` | integer | — | 1 | Neighbor hop depth |
| `memory_find_path` † | `from_id` | string | ✅ | — | Source node identifier |
| | `to_id` | string | ✅ | — | Target node identifier |
| | `max_hops` | integer | — | 6 | Maximum path length (hops) |
| `memory_traverse_graph` | `start_id` | string | ✅ | — | Starting node identifier |
| | `algorithm` | string `"bfs"`\|`"dfs"` | — | `"bfs"` | Traversal algorithm |
| | `max_depth` | integer | — | 3 | Maximum traversal depth |

> † `memory_find_path` (A* pathfinding) is **tier-gated**: lower tiers receive an in-band `-32002 forbidden` error. Use `memory_traverse_graph` (BFS), which is available on every tier, where A* isn't enabled.

### Graph Direct (low-level triple store)

| Tool | Parameter | Type | Req | Default | Description |
|------|-----------|------|:---:|---------|-------------|
| `memory_graph_add_triple` | `subject` | string | ✅ | — | Subject node label |
| | `predicate` | string | ✅ | — | Predicate / edge label |
| | `object` | string | ✅ | — | Object node label |
| `memory_graph_neighbors` | `node` | string | ✅ | — | Starting node label |
| | `depth` | integer | — | 1 | Hop depth (1–5; capped at 5) |
| | `direction` | string `"outgoing"`\|`"incoming"`\|`"both"` | — | `"outgoing"` | Edge direction |
| `memory_graph_shortest_path` | `from` | string | ✅ | — | Source node label |
| | `to` | string | ✅ | — | Target node label |
| | `undirected` | boolean | — | false | Traverse edges in both directions |

### Procedural Memory

| Tool | Parameter | Type | Req | Default | Description |
|------|-----------|------|:---:|---------|-------------|
| `memory_store_procedure` | `name` | string | ✅ | — | Procedure name |
| | `description` | string | — | — | Description |
| | `steps` | array&lt;string\|object&gt; | — | `[]` | Ordered steps: plain strings, or objects `{action, tool?, expected_output?}` |
| | `tags` | array&lt;string&gt; | — | `[]` | Tags |
| | `preconditions` | array&lt;string&gt; | — | `[]` | Preconditions |
| `memory_get_procedure` | `procedure_id` | string | ✅* | — | Procedure UUID — *one of `procedure_id` / `name` required* |
| | `name` | string | ✅* | — | Procedure name (alternative to `procedure_id`) |
| `memory_match_procedure` | `task` | string | ✅ | — | Task description to match against stored procedures |
| | `limit` | integer | — | 5 | Max procedures to return |
| `memory_update_procedure` | `procedure_id` | string | ✅* | — | Procedure UUID to update — *one of `procedure_id` / `name` required* |
| | `name` | string | ✅* | — | Procedure name (alternative to `procedure_id`) |
| | `steps` | array&lt;string\|object&gt; | ✅ | — | New ordered steps (replaces old; creates a new version) |
| | `reason` | string | — | — | Reason for the update |

### Working Memory

| Tool | Parameter | Type | Req | Default | Description |
|------|-----------|------|:---:|---------|-------------|
| `memory_set_working` | `key` | string | ✅ | — | Working memory key |
| | `content` | string | ✅ | — | Value to store (`value` accepted as a legacy alias; non-strings are JSON-encoded) |
| | `ttl_seconds` | integer | — | none (no expiry) | Time-to-live in seconds |
| | `session_id` | string | — | — | Optional session scope |
| `memory_get_working` | `key` | string | ✅ | — | Key to fetch (returns `found:false` if absent/expired) |
| `memory_list_working` | *(none)* | — | — | — | Lists all live working-memory items |
| `memory_clear_working` | `key` | string | — | — | Key to delete; **omit to clear ALL** working memory |

### Pheromone

| Tool | Parameter | Type | Req | Default | Description |
|------|-----------|------|:---:|---------|-------------|
| `memory_deposit_pheromone` | `node_id` | string | ✅ | — | Episode UUID or entity name/ID to reinforce |
| | `strength` | number | — | 1.0 | Pheromone deposit strength |
| `memory_get_pheromone` | `node_id` | string | ✅ | — | Episode UUID or entity name/ID to query |

### Shared Memory Spaces (JWT auth required)

| Tool | Parameter | Type | Req | Default | Description |
|------|-----------|------|:---:|---------|-------------|
| `memory_create_shared_space` | `name` | string | ✅ | — | Space name (1–128 characters) |
| `memory_join_shared_space` | `space_id` | string | ✅ | — | Space ID to join (JWT must grant access to it) |
| | `role` | string `"owner"`\|`"writer"`\|`"reader"` | — | `"writer"` | Requested role |
| `memory_shared_store_entity` | `space_id` | string | ✅ | — | Space ID (requires writer/owner role) |
| | `name` | string | ✅ | — | Entity name |
| | `entity_type` | string | — | `"thing"` | Entity type |
| | `description` | string | — | — | Description |
| `memory_shared_query` | `space_id` | string | ✅ | — | Space ID (requires reader/writer/owner role) |
| | `query` | string | — | `""` (list all) | Search query; empty/omitted lists all entities |
| | `limit` | integer | — | 10 | Max results |
| `memory_list_shared_spaces` | *(none)* | — | — | — | Lists shared spaces the agent belongs to |

### Utility

| Tool | Parameter | Type | Req | Default | Description |
|------|-----------|------|:---:|---------|-------------|
| `memory_get_stats` | *(none)* | — | — | — | Usage stats, memory counts, rate-limit status |
| `memory_delete_agent` | `confirm` | boolean | ✅ | — | Must be `true` to permanently delete all of this agent's memory (irreversible, GDPR) |

## Response Shapes (all 35 tools)

The top-level keys in each tool's success payload (the `structuredContent` object — see
[Tool call response](#mcp-protocol-details)). All shapes are verified against the live server.
Failures instead return `isError:true` + `structuredContent.error{code,type,message}` (see [Edge Cases](#edge-cases)).

### Episodic
| Tool | Success payload (`structuredContent`) |
|------|----------------------------------------|
| `memory_store_episode` | `{ stored:true, id:"<uuid>", ids:["<uuid>", …], chunks:<int>, agent_id }` — `id` = first/only episode; `ids`/`chunks` reflect auto-chunking |
| `memory_get_episodes` | `{ episodes:[ <Episode> … ], count:<int> }` *(outputSchema)* |
| `memory_search_episodes` | `{ results:[ { episode, score, … } … ], count:<int>, retrieval:"hybrid"\|"tfidf" }` *(outputSchema)* |
| `memory_search_timeline` | `{ episodes:[ … ], count:<int>, window:{ start, end } }` |
| `memory_consolidate_episodes` | `{ consolidated:<int>, before:"<rfc3339>", note }` |

### Entity
| Tool | Success payload |
|------|-----------------|
| `memory_store_entity` | `{ id:"<uuid>", entity_id, stored:true }` |
| `memory_get_entity` | found → `{ entity:<Entity>, found:true }` · absent → `{ found:false, entity_id }` |
| `memory_list_entities` | `{ entities:[ … ], count:<int> }` *(outputSchema)* |
| `memory_store_relation` | `{ id:"<uuid>", from_id, to_id, predicate, stored:true }` |
| `memory_get_relations` | `{ relations:[ … ], count:<int>, entity_id }` |

### Graph Operations
| Tool | Success payload |
|------|-----------------|
| `memory_query_graph` | Backend graph-query result object (matched nodes/edges; shape is backend-defined) |
| `memory_semantic_search` | `{ results:[ { entity, score } … ], count:<int> }` *(outputSchema)* |
| `memory_get_neighbors` | `{ neighbors:[ … ], count:<int>, entity_id, hops:<int> }` |
| `memory_find_path` | `{ path:[ … ], hops:<int>, from_id, to_id }` *(Pro+; else in-band `-32002`)* |
| `memory_traverse_graph` | `{ visited:[ … ], count:<int>, start_id, algorithm, max_depth:<int> }` |

### Graph Direct
| Tool | Success payload |
|------|-----------------|
| `memory_graph_add_triple` | `{ stored:true, triple_id:"<uuid>", subject, predicate, object }` |
| `memory_graph_neighbors` | `{ node, depth:<int>, direction, count:<int>, neighbors:[ { subject, predicate, object } … ] }` |
| `memory_graph_shortest_path` | `{ from, to, undirected:<bool>, found:<bool>, hops:<int>, path:[ … ] }` |

### Procedural
| Tool | Success payload |
|------|-----------------|
| `memory_store_procedure` | `{ id:"<uuid>", name, stored:true }` |
| `memory_get_procedure` | found → `{ procedure:<Procedure>, found:true }` · absent → `{ found:false, procedure_id }` |
| `memory_match_procedure` | `{ results:[ … ], count:<int> }` |
| `memory_update_procedure` | `{ new_id:"<uuid>", old_procedure_id, updated:true }` *(creates a new version)* |

### Working
| Tool | Success payload |
|------|-----------------|
| `memory_set_working` | `{ key, set:true, ttl_seconds }` |
| `memory_get_working` | found → `{ item:<WorkingItem>, found:true }` · absent/expired → `{ found:false, key }` |
| `memory_list_working` | `{ items:[ … ], count:<int> }` |
| `memory_clear_working` | single key → `{ key, removed:<bool> }` · clear-all → `{ cleared:true, keys_deleted:<int> }` |

### Pheromone
| Tool | Success payload |
|------|-----------------|
| `memory_deposit_pheromone` | `{ node_id, new_weight:<float>, node_type:"episode"\|"entity" }` |
| `memory_get_pheromone` | found → `{ node_id, weight:<float>, node_type }` · absent → `{ node_id, found:false }` |

### Shared Spaces *(JWT auth)*
| Tool | Success payload |
|------|-----------------|
| `memory_create_shared_space` | `{ space_id, name, owner_did, members:<int>, created_at:"<rfc3339>", status:"created" }` |
| `memory_join_shared_space` | `{ space_id, agent_did, role, members:<int>, status:"joined" }` |
| `memory_shared_store_entity` | `{ space_id, entity_id:"<uuid>", name, entity_type, stored_by, status:"stored" }` |
| `memory_shared_query` | `{ space_id, query, count:<int>, results:[ { id, name, entity_type, description, score? } … ] }` *(`score` present only for non-empty queries)* |
| `memory_list_shared_spaces` | `{ agent_did, count:<int>, spaces:[ { space_id, name, owner_did, my_role, member_count, created_at } … ] }` |

### Utility
| Tool | Success payload |
|------|-----------------|
| `memory_get_stats` | `{ agent_id, tier, monthly_ops_used:<int>, monthly_op_limit:<int>, memory:{ episode_count, entity_count, relation_count, procedure_count, working_count } }` *(outputSchema)* |
| `memory_delete_agent` | `{ agent_id, deleted:true, note }` |

## MCP Protocol Details

**Endpoint:** `POST https://am-server-jbneh74b5q-uc.a.run.app/mcp`
**Auth:** `X-API-Key: am_xxxxxxxxxxxxxxxx`

**Protocol version negotiation** — the server implements the current MCP spec and negotiates the protocol version on `initialize`. It accepts versions up to the release candidate **`2026-07-28`** and defaults to **`2025-11-25`** when the client omits or requests an unknown version (it returns a supported version rather than erroring):

```json
{ "jsonrpc": "2.0", "id": 1, "method": "initialize",
  "params": { "protocolVersion": "2026-07-28", "capabilities": {},
              "clientInfo": { "name": "my-client", "version": "1.0" } } }
```

**Tool call request:**
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

**Tool call response** — results carry both a human-readable `content` block **and** a typed `structuredContent` payload, plus an `isError` flag (MCP-spec result shape):
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{ "type": "text", "text": "{\"stored\":true,\"id\":\"5d9d...\"}" }],
    "isError": false,
    "structuredContent": { "stored": true, "id": "5d9d...", "ids": ["5d9d..."], "chunks": 1 }
  }
}
```

**Errors are reported in-band** — a failing tool call returns `isError: true` with a structured error in `structuredContent.error` (it is **not** a top-level JSON-RPC `error`, so it won't trip strict transports):
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{ "type": "text", "text": "validation error on 'task': required field missing or invalid" }],
    "isError": true,
    "structuredContent": { "error": { "code": -32004, "type": "validation_error",
                                       "message": "validation error on 'task': ..." } }
  }
}
```
(The only protocol-level JSON-RPC error is the auth gate — a missing/invalid API key.)

**Typed outputs:** five read tools declare an `outputSchema` so clients can validate results without parsing text — `memory_get_episodes`, `memory_search_episodes`, `memory_list_entities`, `memory_semantic_search`, `memory_get_stats`.

**Tools list:** `POST /mcp` with `{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}`

## Shared Spaces & JWT Authentication

The five `memory_*_shared_*` / `memory_create_shared_space` / `memory_join_shared_space` tools are
**multi-agent** and need a different credential than the rest of the API.

- **Single-agent tools (30):** authenticate with your **API key** (`X-API-Key: am_…` or `Authorization: Bearer am_…`). Fully self-serve via `POST /v1/keys`.
- **Shared-space tools (5):** require a **JWT** (`Authorization: Bearer <jwt>`). An API-key-only request to any shared-space tool returns an **in-band** error:

  ```json
  { "isError": true,
    "structuredContent": { "error": { "code": -32001, "type": "unauthorized",
      "message": "unauthorized: Shared space operations require JWT authentication. Use 'Authorization: Bearer <jwt>' with a valid JWT token." } } }
  ```

### How to obtain a JWT (important — read this)

> **There is no public self-serve JWT endpoint.** `POST /v1/keys` only issues API keys. JWTs are **HS256** tokens signed with the server's `JWT_SECRET`, which is held by the **Agentverse / ASI Chain identity layer** (or, for self-hosted/BYOC deployments, by whoever configured `JWT_SECRET`). In practice you obtain a shared-space JWT through Agentverse identity onboarding / enterprise provisioning — **shared spaces are not self-serviceable with just a free API key today.** If you only have an API key, use the 30 single-agent tools (all four memory types + graph work fully with an API key).

If you *do* control the signing secret (self-hosted, enterprise, or testing), mint a conformant token with these claims — the server **pins HS256** and **requires** `sub`, `iss`, `aud`, `exp`, `iat`:

| Claim | Required | Value / meaning |
|-------|:---:|-----------------|
| `sub` | ✅ | Agent DID — e.g. `did:fetch:agent123abc`. Becomes the space owner/member identity. |
| `iss` | ✅ | Must be exactly `agentverse-memory`. |
| `aud` | ✅ | Must be exactly `am-server`. |
| `spaces` | — | Array of space IDs this token may access (`[]` when first creating a space). `join`/`store`/`query` require the target `space_id` to be present here. |
| `tier` | — | `explorer`\|`builder`\|`pro`\|`enterprise`. Defaults to `pro` for JWT-authenticated agents. |
| `exp` | ✅ | Expiry (Unix seconds, **numeric** — string `exp` is rejected, CVE-2026-25537). |
| `iat` | ✅ | Issued-at (Unix seconds). |

```json
{ "sub": "did:fetch:agent123abc", "iss": "agentverse-memory", "aud": "am-server",
  "spaces": ["space-id-1"], "tier": "pro", "exp": 1700000000, "iat": 1699900000 }
```

Wrong `iss`/`aud`/signature, an expired token, or a missing required claim are rejected at the auth gate
(`jwt_invalid_issuer` / `jwt_invalid_audience` / `jwt_invalid_signature` / `jwt_expired` / `jwt_missing_claim`).

### Typical multi-agent flow

1. **Owner** (JWT) → `memory_create_shared_space {name}` → returns `space_id`.
2. The identity layer issues each collaborator a JWT whose `spaces` claim **includes that `space_id`** (the server checks `spaces` membership, then the per-space role).
3. **Members** (JWT) → `memory_join_shared_space {space_id, role}` → roles: `owner` > `writer` > `reader`.
4. **Writers/owners** → `memory_shared_store_entity {space_id, name, …}`; **readers+** → `memory_shared_query {space_id, query}`; any member → `memory_list_shared_spaces`.

Insufficient role within a space returns an in-band `-32002` (`forbidden`). Self-hosting? Set `JWT_SECRET` to enable JWT auth; if it is unset, JWT auth (and therefore shared spaces) is disabled.

## Pricing

| Tier | Price | Ops/month | Agents | Graph | A* pathfinding | Shared spaces |
|------|-------|-----------|--------|-------|----------------|---------------|
| **Explorer** | Free | 50,000 | 3 | ✅ + BFS traversal | ❌ | ❌ |
| **Builder** | $19/mo | 500,000 | 25 | ✅ | ✅ A* | ✅ |
| **Pro** | $99/mo | 5,000,000 | Unlimited | ✅ | ✅ A* | ✅ Unlimited |
| **Enterprise** | Custom | Custom | Unlimited | ✅ | ✅ | ✅ |

- All 4 memory types **and** knowledge-graph triples are available on **every tier, including free** — that's the core differentiator vs vector-only free tiers.
- **Builder** adds A* pathfinding + shared spaces; overage billed at **$0.005 / 1K ops**.
- **Pro** adds Active Inference + cross-agent queries.
- **Enterprise** adds SLA, SOC 2, and BYOC (Bring Your Own Cloud).

Get started free: `POST /v1/keys` with `"tier": "explorer"`.

## API Reference

Verified documentation (all live):

- Docs home: https://fetchai.github.io/agentverse-memory/
- Docs index: https://fetchai.github.io/agentverse-memory/docs/
- MCP integration guide: https://fetchai.github.io/agentverse-memory/docs/mcp
- Python SDK docs (SDK publish pending): https://fetchai.github.io/agentverse-memory/docs/python-sdk

## How It Works

1. **Write path ($0, <5ms)**: Content → TF-IDF keyword extraction → embedded `sled` store. **No LLM and no embedding inference at write time** — ingestion is free and fast.
2. **Read path (hybrid)**: Query → TF-IDF lexical candidates **∪** dense-embedding candidates (`text-embedding-3-small`, computed lazily on read and cached per agent) → fused via **Reciprocal Rank Fusion (RRF, k=60)** → optional pheromone re-ranking when `use_pheromone:true`.
3. **Graph**: Knowledge triples form an in-memory graph; BFS traversal is available on every tier, A* pathfinding (pheromone/shortest/semantic strategies) on Builder+.
4. **Pheromone decay**: `w(t) = w₀ × exp(-Δt/τ)` — lazy computation at query time, no background daemon. Pheromone re-ranking is **opt-in** (default off) and most valuable for warm-cache / repeated-access and multi-agent shared workloads.
5. **Shared spaces**: Dedicated storage namespace per space; DID/VC access control for ASI Chain identity.

> **Cost note:** Because embeddings are computed on the read path and cached — never at write time — ingesting a large corpus costs **$0** in LLM/embedding fees and writes stay under 5ms. An internal within-harness benchmark (LOCOMO) measured hybrid retrieval lifting answer quality **+4.8pp overall / +7.5pp single-hop** versus lexical-only, while preserving the zero-LLM-write property. (Internal, within-harness measurement — not a cross-vendor accuracy claim.)

## Edge Cases

- **Rate limits**: 429 response — check `X-RateLimit-Reset` header and retry after reset
- **No / bad API key**: 401 response — set `AM_API_KEY` and ensure it starts with `am_`
- **Tool execution error**: returned in-band as `isError:true` + `structuredContent.error{code,type,message}` (HTTP 200), e.g. `-32004` for argument-validation failures — fix the arguments and retry
- **Unknown tool name**: top-level JSON-RPC `-32601` ("unknown tool") — verify the name matches the 35-tool list (all lowercase, `memory_` prefix)
- **Tier-gated feature**: in-band `-32002` ("forbidden: tier ... cannot access ...") — e.g. A* `find_path` on the free tier; upgrade or use BFS `traverse_graph`
- **Large content**: episode content limited to 64KB; triple subject/predicate/object to 1KB each
- **Temporal filter**: `valid_at` ISO 8601 string — use `Z` suffix for UTC

## References

- [Agentverse Memory Docs](https://fetchai.github.io/agentverse-memory/)
- [MCP Integration Guide](https://fetchai.github.io/agentverse-memory/docs/mcp)
- [Agentverse Platform](https://agentverse.ai)
