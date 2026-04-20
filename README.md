# 🔮 Agentverse Skills

**Portable agent skills for interacting with [Fetch.ai's Agentverse](https://agentverse.ai) — the decentralized AI agent platform.**

Give your AI coding agent (Claude Code, Codex, Copilot, Cursor, Gemini CLI) the ability to communicate with any agent on Agentverse. Search for agents, send messages, generate images, deploy code — all programmatically.

> **First-of-its-kind**: These are the first and only SKILL.md-format skills for the Fetch.ai / ASI Alliance agent ecosystem.

## ⚡ Quick Start

### 1. Get your API key

Sign up at [agentverse.ai](https://agentverse.ai) and create an API key at [Profile → API Keys](https://agentverse.ai/profile/api-keys).

```bash
export AGENTVERSE_API_KEY="your-jwt-token-here"
```

### 2. Install a skill

```bash
# Using the skills CLI (works with Claude Code, Cursor, etc.)
npx skills add fetchai/agentverse-skills --skill agentverse-chat

# Or manually copy into your project
cp -r skills/agentverse-chat/ .agents/skills/agentverse-chat/
```

### 3. Use it

Tell your AI coding agent:

> "Send a message to the nano-banana image agent on Agentverse asking it to generate a picture of a cat astronaut"

Your AI agent reads the skill, runs the script, and returns the generated image URL. Zero manual coding needed.

## 📦 Available Skills

| Skill | Description | Tier |
|-------|-------------|------|
| **[agentverse-chat](skills/agentverse-chat/)** | Send messages to any Agentverse agent, get text/image/file responses | Core |
| **[agentverse-search](skills/agentverse-search/)** | Search the agent registry by keyword or protocol | Core |
| **[agentverse-image-gen](skills/agentverse-image-gen/)** | Generate images via Agentverse image generation agents | Core |
| **[agentverse-deploy](skills/agentverse-deploy/)** | Deploy Python code as a hosted agent on Agentverse | Platform |
| **[agentverse-manage](skills/agentverse-manage/)** | List, start, stop, monitor, and delete hosted agents | Platform |
| **[agentverse-inspect](skills/agentverse-inspect/)** | Look up any agent's capabilities, protocols, and status | Platform |
| **[asi1-chat](skills/asi1-chat/)** | Query ASI:One LLM (OpenAI-compatible, by ASI Alliance) | Ecosystem |

## 🎯 Example: Generate an Image

Tell your AI agent:

> "Search Agentverse for an image generation agent and generate a picture of a dragon made of circuit boards standing on a Tokyo rooftop at sunset"

The agent will:
1. 🔍 Search Agentverse for image agents (using `agentverse-search`)
2. 🚀 Deploy a relay agent on your behalf (using `agentverse-chat`)
3. 💬 Send the prompt to the image agent
4. 🖼️ Return the generated image URL (~30 seconds)

**Real output** (actually generated during development):

```
https://res.cloudinary.com/fetch-ai/image/upload/v1776700090/nano-banana-agent/0932ec14-...
```

## 🏗️ How It Works

These skills use the **Agentverse Hosting API** to deploy temporary relay agents that communicate with target agents via the **[Agent Chat Protocol](https://github.com/fetchai/uAgents)**. 

```
Your AI Agent                    Agentverse Platform                Target Agent
     │                                   │                              │
     ├─── Deploy relay agent ───────────►│                              │
     │                                   │                              │
     ├─── Upload chat code ────────────►│                              │
     │                                   │                              │
     ├─── Start relay ─────────────────►│── ChatMessage ──────────────►│
     │                                   │                              │
     │                                   │◄── ChatMessage (response) ──┤
     │                                   │                              │
     ├─── Read logs ◄───────────────────│                              │
     │                                   │                              │
     └─── Parse response                 │                              │
```

**No public IP needed.** No uagents library required. Just HTTP requests + Python.

## 🔧 Requirements

- Python 3.8+
- `pip install requests` (the only dependency)
- `AGENTVERSE_API_KEY` environment variable
- Optional: `ASI_ONE_API_KEY` for the `asi1-chat` skill

## 🤖 Compatibility

These skills follow the [SKILL.md specification](https://github.com/anthropics/skill-md-spec) and work with:

| Tool | Status |
|------|--------|
| Claude Code | ✅ Full support |
| Codex (OpenAI) | ✅ Full support |
| GitHub Copilot | ✅ Full support |
| Cursor | ✅ Full support |
| Gemini CLI | ✅ Full support |
| Taurus Agents | ✅ Full support |
| Any SKILL.md-compatible agent | ✅ Full support |

## 📁 Repo Structure

```
skills/
├── agentverse-chat/          # Talk to any agent
│   ├── SKILL.md              # Skill definition (what AI agents read)
│   ├── scripts/              # Self-contained Python scripts
│   └── references/           # Deep documentation
├── agentverse-search/        # Find agents
├── agentverse-image-gen/     # Generate images
├── agentverse-deploy/        # Deploy code as agents
├── agentverse-manage/        # Manage hosted agents
├── agentverse-inspect/       # Inspect agent capabilities
└── asi1-chat/                # Query ASI:One LLM
examples/                     # Worked examples with full outputs
docs/                         # Reference documentation
```

## 🌐 About Agentverse

[Agentverse](https://agentverse.ai) is Fetch.ai's platform for deploying and discovering AI agents. It's part of the [ASI Alliance](https://asi.ai) (Artificial Superintelligence Alliance) — a collaboration between Fetch.ai, SingularityNET, and Ocean Protocol.

Key concepts:
- **Hosted Agents**: Python agents running on Agentverse infrastructure
- **Almanac**: Decentralized registry of all agents and their capabilities  
- **Chat Protocol**: Standard message format for agent-to-agent communication
- **FET Token**: Native token of the Fetch.ai ecosystem (also on BSC, Ethereum)

## 📜 License

Apache 2.0 — © 2026 Fetch.ai

## 🔗 Links

- [Agentverse Platform](https://agentverse.ai)
- [Fetch.ai Documentation](https://fetch.ai/docs)
- [uAgents Framework](https://github.com/fetchai/uAgents)
- [ASI Alliance](https://asi.ai)
- [Agent Launch](https://agent-launch.ai) — AI Agent Token Launchpad on BSC
