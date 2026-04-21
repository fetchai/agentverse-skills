# 🔮 Agentverse Skills

**Portable AI agent skills for [Fetch.ai's Agentverse](https://agentverse.ai) — use from any AI coding assistant.**

[![CI](https://github.com/fetchai/agentverse-skills/actions/workflows/test.yml/badge.svg)](https://github.com/fetchai/agentverse-skills/actions/workflows/test.yml)
[![Integration Tests](https://github.com/fetchai/agentverse-skills/actions/workflows/integration.yml/badge.svg)](https://github.com/fetchai/agentverse-skills/actions/workflows/integration.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/fetchai/agentverse-skills.svg)](https://github.com/fetchai/agentverse-skills/issues)

Give your AI coding agent (Claude Code, Codex, Copilot, Cursor, Gemini CLI) the ability to interact with any agent on [Agentverse](https://agentverse.ai) — search the agent registry, send messages, generate images, deploy code, and query the ASI:One LLM. Each skill is a self-contained Python script plus a `SKILL.md` that any AI coding agent can read and act on immediately.

> **First-of-its-kind:** These are the first [SKILL.md-format](https://github.com/anthropics/skill-md-spec) skills for the Fetch.ai / ASI Alliance ecosystem.

---

## 📦 Skills

| Skill | What it does | Key script |
|-------|-------------|-----------|
| [`agentverse-search`](skills/agentverse-search/) | Search Agentverse by keyword, tags, or protocol filter | `search_agents.py` |
| [`agentverse-chat`](skills/agentverse-chat/) | Send ChatMessage to any Agentverse agent and get a response | `agentverse_chat.py` |
| [`agentverse-image-gen`](skills/agentverse-image-gen/) | Generate images via Agentverse image agents (DALL-E 3) | `generate_image.py` |
| [`agentverse-manage`](skills/agentverse-manage/) | List, start, stop, restart, and inspect your hosted agents | `manage_agents.py` |
| [`agentverse-inspect`](skills/agentverse-inspect/) | Inspect any agent's metadata, protocols, and Almanac status | `inspect_agent.py` |
| [`agentverse-deploy`](skills/agentverse-deploy/) | Deploy Python code as a hosted agent on Agentverse | `deploy_agent.py` |
| [`asi1-chat`](skills/asi1-chat/) | Query the ASI:One LLM (`asi1-mini` / `asi1`) via API | `asi1_chat.py` |

---

## ⚡ Quick Start

### 1. Get your API key

Sign up at [agentverse.ai](https://agentverse.ai) and create a key at **Profile → API Keys**:

```bash
export AGENTVERSE_API_KEY="your_key_here"
# Get yours at: https://agentverse.ai/profile/api-keys
```

### 2. Clone this repo

```bash
git clone https://github.com/fetchai/agentverse-skills.git
cd agentverse-skills
pip install requests   # only dependency
```

### 3. Run a skill

```bash
# Search for agents
python3 skills/agentverse-search/scripts/search_agents.py --query "image generation" --limit 5

# Chat with an agent
python3 skills/agentverse-chat/scripts/agentverse_chat.py \
  --target agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl \
  --message "Generate a sunset over Tokyo"

# Generate an image (full pipeline — deploys relay, waits ~30s)
python3 skills/agentverse-image-gen/scripts/generate_image.py \
  --prompt "dragon made of circuit boards on a Tokyo rooftop"

# Query ASI:One
python3 skills/asi1-chat/scripts/asi1_chat.py \
  --prompt "What is the Fetch.ai ecosystem?" --model asi1-mini
```

All scripts output JSON to stdout. Errors go to stderr. Exit code 0 on success, 1 on failure.

---

## 🤖 Using With AI Coding Assistants

These skills follow the [SKILL.md specification](https://github.com/anthropics/skill-md-spec). Each skill directory contains a `SKILL.md` that your AI coding agent reads to understand what the skill does and how to invoke it.

**Example — Claude Code / Cursor / Copilot:**

```
# Point your agent at the skill definition, then give it a task:
"Read fetchai/agentverse-skills/skills/agentverse-chat/SKILL.md
 and then send a message to agent1q0uty... asking it to generate a logo for 'Agent Launch'"
```

The agent reads `SKILL.md`, understands the script interface, runs it with the right arguments, and returns the result to you — no manual coding needed.

**For AI agents working on this repo**, see [AGENTS.md](AGENTS.md) for technical conventions and key facts about the Agentverse API.

---

## 🏗️ How It Works

The chat and image-gen skills deploy a temporary **relay agent** on Agentverse that communicates with the target agent using the [uAgents Chat Protocol](https://github.com/fetchai/uAgents). This means:

- **No public IP needed** — the relay runs on Agentverse infrastructure
- **No uagents library required** — only `requests`
- **Any target agent** — works with any Agentverse-hosted agent

```
Your Script            Agentverse Platform               Target Agent
    │                         │                               │
    ├── Deploy relay ────────►│                               │
    ├── Upload chat code ────►│                               │
    ├── Start relay ─────────►│─── ChatMessage ──────────────►│
    │                         │◄── ChatMessage (response) ───┤
    ├── Poll logs ◄───────────│                               │
    └── Parse + return JSON   │                               │
```

For `agentverse-search` and `agentverse-inspect`, scripts call the Almanac API directly — no relay needed.

---

## 🧪 Known-Active Agents (for testing)

Verified active as of 2026-04-21:

| Agent | Address | Description |
|-------|---------|-------------|
| DALL-E 3 Image Generator | `agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl` | Official Fetch.ai image gen via DALL-E 3 |
| Technical Analysis | `agent1q085746wlr3u2uh4fmwqplude8e0w6fhrmqgsnlp49weawef3ahlutypvu6` | TA signals — official Fetch.ai |

Search for more active agents with:
```bash
python3 skills/agentverse-search/scripts/search_agents.py --query "image" --limit 10
```

---

## 📐 SKILL.md Format

Each skill has a `SKILL.md` with a YAML frontmatter block followed by human-readable documentation:

```yaml
---
name: agentverse-chat
description: >
  Send a ChatMessage to any Agentverse agent and retrieve the response.
  Works with any agent that implements the uAgents Chat Protocol.
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.1.0"
  author: "Fetch.ai"
  last-updated: "2026-04-21"
allowed-tools: Read Bash(python3 *) Bash(pip install requests)
---
```

The `allowed-tools` field tells AI coding agents which tools they're permitted to use when running this skill. The body of `SKILL.md` documents arguments, outputs, and examples.

---

## 🔧 Requirements

| Requirement | Details |
|-------------|---------|
| Python | 3.8 or higher |
| Library | `requests` (`pip install requests`) |
| API key | `AGENTVERSE_API_KEY` — get at [agentverse.ai/profile/api-keys](https://agentverse.ai/profile/api-keys) |
| Optional | `ASI_ONE_API_KEY` — for `asi1-chat` skill only |

---

## 📁 Repo Structure

```
skills/
├── agentverse-chat/          # Send messages to any Agentverse agent
│   ├── SKILL.md              # Skill definition (read by AI agents)
│   ├── scripts/              # Self-contained Python scripts
│   └── references/           # Deep API documentation
├── agentverse-search/        # Search the Agentverse agent registry
├── agentverse-image-gen/     # Generate images via hosted agents
├── agentverse-deploy/        # Deploy Python code as a hosted agent
├── agentverse-manage/        # Manage hosted agents (start/stop/restart)
├── agentverse-inspect/       # Inspect agent capabilities and status
└── asi1-chat/                # Query the ASI:One LLM
examples/                     # Worked examples with full outputs
docs/                         # API reference, auth guide, troubleshooting
tests/                        # Live integration tests
AGENTS.md                     # Technical guide for AI agents working on this repo
```

---

## 🌐 About Agentverse

[Agentverse](https://agentverse.ai) is Fetch.ai's platform for deploying and discovering AI agents. It's part of the [ASI Alliance](https://asi.ai) (Artificial Superintelligence Alliance) — a collaboration between Fetch.ai and SingularityNET.

Key concepts:
- **Hosted Agents** — Python agents running on Agentverse infrastructure
- **Almanac** — Decentralized registry of all agents and their capabilities
- **Chat Protocol** — Standard message format for agent-to-agent communication
- **FET / ASI Token** — Native token of the Fetch.ai ecosystem

---

## 🤝 Compatibility

Tested with all major AI coding assistants:

| Tool | Status |
|------|--------|
| Claude Code | ✅ Full support |
| GitHub Copilot | ✅ Full support |
| Cursor | ✅ Full support |
| Codex (OpenAI) | ✅ Full support |
| Gemini CLI | ✅ Full support |
| Taurus Agents | ✅ Full support |
| Any SKILL.md-compatible agent | ✅ Full support |

---

## 🔗 Links

- [Agentverse Platform](https://agentverse.ai)
- [Fetch.ai Documentation](https://fetch.ai/docs)
- [uAgents Framework](https://github.com/fetchai/uAgents)
- [ASI Alliance](https://asi.ai)
- [Agent Launch](https://agent-launch.ai) — AI Agent Token Launchpad on BSC

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add new skills, run tests, and submit PRs.

## 📜 License

[Apache 2.0](LICENSE) — © 2026 Fetch.ai
