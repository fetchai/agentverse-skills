# Instructions for AI Agents Working on This Repo

## What This Repo Is

This is a collection of **portable agent skills** (SKILL.md format) that enable AI coding agents to interact with [Fetch.ai's Agentverse](https://agentverse.ai) platform programmatically.

## Repo Structure

- `skills/` — Each subdirectory is a self-contained skill
  - `SKILL.md` — The skill definition (what you read to learn the skill)
  - `scripts/` — Runnable Python scripts (only dependency: `requests`)
  - `references/` — Deep documentation and protocol details
- `examples/` — Worked examples showing real outputs
- `docs/` — Reference documentation (API, auth, troubleshooting)

## How to Add a New Skill

1. Create `skills/<skill-name>/SKILL.md` with proper frontmatter
2. Create `skills/<skill-name>/scripts/<script>.py` — self-contained, CLI-ready
3. Add entry to the table in `README.md`
4. Add a worked example in `examples/` if non-trivial

## Skill Script Requirements

- **Self-contained**: Only needs `requests` library (stdlib + requests)
- **CLI interface**: Uses `argparse`, runnable from command line
- **JSON output**: Results go to stdout as valid JSON
- **Error handling**: Logs/errors go to stderr, exit code 1 on failure
- **Env vars**: Uses `AGENTVERSE_API_KEY` (or `ASI_ONE_API_KEY` for ASI:One)
- **Helpful errors**: If env var missing, print instructions on how to get one
- **Apache 2.0 license header**

## SKILL.md Format

Follow the [SKILL.md specification](https://github.com/anthropics/skill-md-spec):

```yaml
---
name: skill-name
description: >
  One-paragraph description of what this skill does.
  Include trigger phrases and key capabilities.
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-04-20"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---
```

## Key Technical Facts

- **Base URL**: `https://agentverse.ai`
- **Auth**: `Authorization: Bearer {AGENTVERSE_API_KEY}`
- **Working API version**: V1 (`/v1/hosting/agents`, `/v1/almanac/...`)
- **Code upload format**: `{"code": json.dumps([{"language":"python","name":"agent.py","value":"..."}])}`
- **Hosted env**: `agent` is pre-created — do NOT use `Agent()` or `.run()`
- **Logs are output**: Use `ctx.logger.info()` — no stdout/stderr in hosted env
- **Image gen timing**: ACK ~1s, text response ~3s, image response ~30s

## Testing

To test a skill script:
```bash
export AGENTVERSE_API_KEY="your-key"
python3 skills/agentverse-search/scripts/search_agents.py --query "image" --limit 5
```

All scripts should output valid JSON on success and exit 0, or print an error to stderr and exit 1.
