# Agentverse Skills

**Portable agent skills for [Fetch.ai's Agentverse](https://agentverse.ai) — usable from any AI coding assistant, or straight from a shell.**

[![CI](https://github.com/fetchai/agentverse-skills/actions/workflows/test.yml/badge.svg)](https://github.com/fetchai/agentverse-skills/actions/workflows/test.yml)
[![Integration Tests](https://github.com/fetchai/agentverse-skills/actions/workflows/integration.yml/badge.svg)](https://github.com/fetchai/agentverse-skills/actions/workflows/integration.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Eight self-contained skills for talking to the Agentverse platform: search the agent
registry, message any agent, generate images, deploy and manage hosted agents, inspect
Almanac registrations, query the ASI:One LLM, and give an agent persistent memory.

Each skill is a directory containing a **`SKILL.md`** (a machine-readable description an AI
coding agent can act on) and a **plain Python CLI script**. There is no SDK to learn and no
framework to adopt — the scripts take command-line flags and print one JSON object.

## Contents

- [Skills](#skills)
- [Quick start](#quick-start)
- [Output contract](#output-contract)
- [Using this with an AI coding assistant](#using-this-with-an-ai-coding-assistant)
- [How it works](#how-it-works)
- [Requirements and environment variables](#requirements-and-environment-variables)
- [Repository layout](#repository-layout)
- [Windows / PowerShell](#windows--powershell)
- [Tests](#tests)
- [Continuous integration](#continuous-integration)
- [Documentation and examples](#documentation-and-examples)
- [Agents to test against](#agents-to-test-against)
- [Contributing](#contributing)
- [License](#license)

---

## Skills

| Skill | What it does | Script | Needs |
|-------|--------------|--------|-------|
| [`agentverse-search`](skills/agentverse-search/) | Search the Agentverse registry by keyword, tag or protocol digest; optional semantic search | [`search_agents.py`](skills/agentverse-search/scripts/search_agents.py) | `AGENTVERSE_API_KEY` |
| [`agentverse-chat`](skills/agentverse-chat/) | Send a Chat Protocol message to any Agentverse agent and return its reply | [`agentverse_chat.py`](skills/agentverse-chat/scripts/agentverse_chat.py) | `AGENTVERSE_API_KEY` |
| [`agentverse-image-gen`](skills/agentverse-image-gen/) | Send a prompt to an image-generation agent and return the image URL | [`generate_image.py`](skills/agentverse-image-gen/scripts/generate_image.py) | `AGENTVERSE_API_KEY` |
| [`agentverse-deploy`](skills/agentverse-deploy/) | Upload Python code as a new hosted agent, optionally starting it | [`deploy_agent.py`](skills/agentverse-deploy/scripts/deploy_agent.py) | `AGENTVERSE_API_KEY` |
| [`agentverse-manage`](skills/agentverse-manage/) | `list` / `start` / `stop` / `restart` / `logs` / `delete` / `code` / `info` / `cleanup` for your hosted agents | [`manage_agents.py`](skills/agentverse-manage/scripts/manage_agents.py) | `AGENTVERSE_API_KEY` |
| [`agentverse-inspect`](skills/agentverse-inspect/) | Look an agent up across the Almanac, search index and hosting API in one call | [`inspect_agent.py`](skills/agentverse-inspect/scripts/inspect_agent.py) | `AGENTVERSE_API_KEY` |
| [`asi1-chat`](skills/asi1-chat/) | Query the ASI:One LLM (`asi1`, `asi1-mini`) over an OpenAI-compatible API, with optional streaming | [`asi1_chat.py`](skills/asi1-chat/scripts/asi1_chat.py) | `ASI_ONE_API_KEY` |
| [`agentverse-memory`](skills/agentverse-memory/) | CLI over the Agentverse Memory MCP service: episodic, graph, procedural and working memory | [`memory_client.py`](skills/agentverse-memory/scripts/memory_client.py) | `AM_API_KEY` |

`skills/_common/` is not a skill — it is the shared relay/parsing helper module used by
`agentverse-chat` and `agentverse-image-gen`. CI skips any `skills/` directory whose name
starts with `_` when it checks that every skill has a `SKILL.md`.

Run any script with `--help` to see its full flag list.

---

## Quick start

### 1. Get an API key

Sign in at [agentverse.ai](https://agentverse.ai) and create an API key from your profile,
then export it. Platform documentation lives at
[docs.agentverse.ai](https://docs.agentverse.ai).

```bash
export AGENTVERSE_API_KEY="your_key_here"
```

`asi1-chat` uses a separate key from [asi1.ai](https://asi1.ai), and `agentverse-memory`
uses a third — see [Requirements and environment variables](#requirements-and-environment-variables).

### 2. Clone and install

```bash
git clone https://github.com/fetchai/agentverse-skills.git
cd agentverse-skills
pip install -r requirements.txt   # requests — the only third-party dependency
```

### 3. Run a skill

```bash
# Search the registry
python3 skills/agentverse-search/scripts/search_agents.py --query "image generation" --limit 5

# Ask an agent a question (deploys a relay on Agentverse, so allow ~15-60 s)
python3 skills/agentverse-chat/scripts/agentverse_chat.py \
  --target agent1q085746wlr3u2uh4fmwqplude8e0w6fhrmqgsnlp49weawef3ahlutypvu6 \
  --message "What is the RSI for BTC?" \
  --cleanup

# Generate an image (~60 s)
python3 skills/agentverse-image-gen/scripts/generate_image.py \
  --prompt "dragon made of circuit boards on a Tokyo rooftop" \
  --cleanup

# Query ASI:One
python3 skills/asi1-chat/scripts/asi1_chat.py --prompt "What is the Fetch.ai ecosystem?"

# List your hosted agents
python3 skills/agentverse-manage/scripts/manage_agents.py list
```

Two things worth knowing before your first run:

- **`--cleanup` deletes the relay agent afterwards.** Without it, relay agents accumulate in
  your account. `manage_agents.py cleanup` removes any that are left over.
- **`agentverse-chat` defaults to `--wait 45`**, which is not always enough. A slow agent
  returns `{"status": "timeout"}` with the relay's log entries attached for diagnosis;
  raise `--wait` and try again.

For an image-generation agent use `agentverse-image-gen` rather than `agentverse-chat`: it
waits longer by default (`--wait 90`) and resolves the returned `agent-storage://` resource
into a `public_url` you can open in a browser.

---

## Output contract

Every script prints exactly one JSON object and sets an exit code, which is what makes them
safe to call from an automated agent:

| | |
|---|---|
| **success** | `{"status": "success", ...}` on stdout, exit code **0** |
| **failure** | `{"status": "error", "error": "<message>"}`, exit code **1** |
| **stderr** | `--verbose` progress lines, prefixed `[skill-name]`; otherwise empty |

Failures are reported as JSON like everything else, so parse the output and branch on
`status`, or just check the exit code — no script ever fails silently.

```console
$ python3 skills/agentverse-search/scripts/search_agents.py --query x
{"status": "error", "error": "AGENTVERSE_API_KEY environment variable not set. ..."}
$ echo $?
1
```

Two deliberate exceptions to note when you are wiring this into a pipeline:

- **`memory_client.py`** writes its error JSON to **stderr**, not stdout, and has no
  `--verbose` flag — it uses subcommands (`store-episode`, `query-facts`, `health`, …)
  instead of top-level options. Its `health` subcommand is the one call that works without
  a key.
- **`asi1_chat.py --stream`** streams tokens to stderr as they arrive, then prints the
  complete JSON object to stdout as usual.

---

## Using this with an AI coding assistant

Every skill directory contains a `SKILL.md`: YAML frontmatter followed by human-readable
documentation of the arguments, outputs and failure modes. The frontmatter follows the
[SKILL.md format](https://github.com/anthropics/skills):

```yaml
---
name: agentverse-chat
description: >
  Send messages to any agent on Fetch.ai's Agentverse and receive responses.
  ...
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-04-20"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---
```

`allowed-tools` declares the tools an assistant needs in order to run the skill. Point your
assistant at the file and give it the task:

```
Read skills/agentverse-chat/SKILL.md, then message
agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl
and ask it to generate a logo.
```

Nothing here is assistant-specific: a `SKILL.md` is a markdown file and a skill is a CLI
script, so any tool that can read a file and run `python3` can use them. If you are working
**on** this repository rather than with it, read [AGENTS.md](AGENTS.md) first — it records
the Agentverse API conventions that are easy to get wrong.

---

## How it works

Two of the skills need to receive messages from another agent, which normally requires a
publicly reachable endpoint. They avoid that by deploying a small **relay agent** onto
Agentverse's own hosting, so the network round-trip happens between two hosted agents and
your machine only ever makes outbound HTTPS calls.

```
Your machine              Agentverse hosting              Target agent
     |                            |                            |
     |-- create/find relay ------>|                            |
     |-- upload relay code ------>|                            |
     |-- start relay ------------>|--- ChatMessage ----------->|
     |                            |<-- ChatMessage (reply) ----|
     |-- poll relay logs -------->|                            |
     |<- parse RESULT: lines -----|                            |
```

The relay source is generated by the script and uploaded as agent code; it is the only part
of the system that imports `uagents`, and it runs on Agentverse, not locally. That is why
your machine needs `requests` and nothing else.

| Skill | Mechanism |
|---|---|
| `agentverse-chat`, `agentverse-image-gen` | deploy/reuse a relay agent (`skills/_common/agentverse_relay.py`), then poll its logs |
| `agentverse-search` | `POST https://agentverse.ai/v1/search/agents` |
| `agentverse-inspect` | `GET /v1/almanac/agents/<addr>`, the search API and `/v1/hosting/agents/<addr>/profile` |
| `agentverse-deploy`, `agentverse-manage` | `https://agentverse.ai/v1/hosting/agents` |
| `asi1-chat` | `POST https://api.asi1.ai/v1/chat/completions` |
| `agentverse-memory` | JSON-RPC over the Agentverse Memory MCP endpoint |

Relay agents are named with the prefix `agentverse-skills-relay`, which is how
`manage_agents.py cleanup` finds them.

---

## Requirements and environment variables

| Requirement | Detail |
|---|---|
| Python | 3.8 or newer (CI compiles every script on 3.8, 3.10 and 3.12) |
| Dependency | `requests>=2.28.0` — see [`requirements.txt`](requirements.txt) |

| Variable | Used by | Notes |
|---|---|---|
| `AGENTVERSE_API_KEY` | search, chat, image-gen, deploy, manage, inspect | Bearer token from your Agentverse profile |
| `ASI_ONE_API_KEY` | `asi1-chat` | From [asi1.ai](https://asi1.ai) |
| `AM_API_KEY` | `agentverse-memory` | Agentverse Memory key (`am_…`). `memory_client.py create-key` mints a free one |
| `AM_BASE_URL` | `agentverse-memory` | Optional endpoint override |

A missing key is reported like any other error — JSON on stdout, exit code 1 — so a script
never fails silently. Full authentication notes: [docs/authentication.md](docs/authentication.md).

---

## Repository layout

```
skills/
├── _common/                  # shared relay + log-parsing helpers (not a skill)
├── agentverse-chat/          # SKILL.md, scripts/, references/
├── agentverse-deploy/        # SKILL.md, scripts/
├── agentverse-image-gen/     # SKILL.md, scripts/
├── agentverse-inspect/       # SKILL.md, scripts/
├── agentverse-manage/        # SKILL.md, scripts/
├── agentverse-memory/        # SKILL.md, scripts/
├── agentverse-search/        # SKILL.md, scripts/
└── asi1-chat/                # SKILL.md, scripts/
docs/                         # api-reference.md, authentication.md, troubleshooting.md
examples/                     # four worked end-to-end examples
tests/                        # test_unit.py (offline), test_integration.py (live)
AGENTS.md                     # conventions for AI agents working on this repo
CHANGELOG.md                  # what changed, per release
CONTRIBUTING.md               # how to add a skill and open a PR
```

`agentverse-chat` is currently the only skill with a `references/` directory
([chat-protocol.md](skills/agentverse-chat/references/chat-protocol.md),
[hosted-agent-gotchas.md](skills/agentverse-chat/references/hosted-agent-gotchas.md)).

---

## Windows / PowerShell

Nothing in the scripts is POSIX-specific — they use `requests` and the standard library
only — so the differences are in the shell. Two substitutions cover them: `py` (or
`python`) instead of `python3`, and `$env:` instead of `export`.

```powershell
$env:AGENTVERSE_API_KEY = "your_key_here"
$env:ASI_ONE_API_KEY    = "sk_..."          # only for asi1-chat

py skills/agentverse-search/scripts/search_agents.py --query "weather" --limit 5

# backtick, not backslash, for line continuation
py skills/agentverse-chat/scripts/agentverse_chat.py `
  --target agent1q... `
  --message "Hello" `
  --cleanup
```

| Unix / macOS | Windows PowerShell |
|---|---|
| `export VAR="value"` | `$env:VAR = "value"` |
| `python3 script.py` | `py script.py` |
| `\` line continuation | `` ` `` line continuation |
| `pip3 install -r requirements.txt` | `pip install -r requirements.txt` |

- **`py` not found?** Install Python from [python.org](https://www.python.org/downloads/)
  with "Add Python to PATH" ticked.
- **Variables not persisting?** `$env:` lasts for the session only. Add them to your
  PowerShell profile (`notepad $PROFILE`) or set them under
  **System Properties → Environment Variables**.
- **SSL errors?** `pip install --upgrade certifi pip-system-certs`.

---

## Tests

```bash
python3 tests/test_unit.py          # 19 tests, no network, no credentials
python3 tests/test_integration.py   # live API tests, needs AGENTVERSE_API_KEY
```

`test_unit.py` covers the log-parsing layer that everything else depends on: JSON and
Python-`repr` result entries, UUID stripping, status extraction and relay-name matching.
`test_integration.py` exercises the scripts end to end against the live platform; it
creates and deletes real hosted agents, so it needs a working key. Both files also run
under `pytest` if you prefer it. See [tests/README.md](tests/README.md) for the full matrix.

---

## Continuous integration

| Workflow | Trigger | What it does |
|---|---|---|
| [`test.yml`](.github/workflows/test.yml) | push and PR to `main` | On Python 3.8 / 3.10 / 3.12: byte-compiles every script under `skills/`, parses each one as an AST, and asserts every skill directory has a `SKILL.md` |
| [`integration.yml`](.github/workflows/integration.yml) | push to `main`, or manual dispatch | Live API tests and three smoke tests, gated on the `AGENTVERSE_INTEGRATION_TESTS_ENABLED` repository variable and marked `continue-on-error` |

`test.yml` is a compile-and-structure check — it does **not** execute `tests/test_unit.py`.
Run the unit tests locally before opening a pull request. The badges at the top of this
file report the current state of both workflows.

---

## Documentation and examples

| | |
|---|---|
| [docs/api-reference.md](docs/api-reference.md) | Agentverse endpoints the scripts call, with request and response shapes |
| [docs/authentication.md](docs/authentication.md) | Where each key comes from and how it is sent |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Timeouts, empty replies, relay problems |
| [examples/01-search-and-chat.md](examples/01-search-and-chat.md) | Find an agent, then talk to it |
| [examples/02-image-generation.md](examples/02-image-generation.md) | Prompt to image URL |
| [examples/03-deploy-custom-agent.md](examples/03-deploy-custom-agent.md) | Write, deploy and start a hosted agent |
| [examples/04-multi-agent-workflow.md](examples/04-multi-agent-workflow.md) | Chain several skills together |

---

## Agents to test against

Two long-lived Fetch.ai agents, useful as targets while you are getting set up. Both were
present in the Almanac with `status: active` when this file was last revised
(2026-08-06); agent availability changes, so verify before relying on either.

| Agent | Address |
|---|---|
| DALL-E 3 Image Generator | `agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl` |
| Technical Analysis Agent | `agent1q085746wlr3u2uh4fmwqplude8e0w6fhrmqgsnlp49weawef3ahlutypvu6` |

Check either one, or find others, with the skills themselves:

```bash
python3 skills/agentverse-inspect/scripts/inspect_agent.py \
  --agent agent1q085746wlr3u2uh4fmwqplude8e0w6fhrmqgsnlp49weawef3ahlutypvu6

python3 skills/agentverse-search/scripts/search_agents.py --query "image" --limit 10
```

---

## Contributing

New skills are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers the directory layout, the
`SKILL.md` template, the script requirements (self-contained, `requests`-only, JSON on
stdout) and the pull-request checklist. Bugs and requests go to
[Issues](https://github.com/fetchai/agentverse-skills/issues).

---

## About Agentverse

[Agentverse](https://agentverse.ai) is Fetch.ai's platform for building, hosting and
discovering AI agents, and part of the [ASI Alliance](https://superintelligence.io).

- **Hosted agents** — Python agents running on Fetch.ai infrastructure, no server of your own
- **Almanac** — the registry of agents, their endpoints and supported protocols
- **Chat Protocol** — the message format agents use to talk to each other
- **ASI:One** — the ASI Alliance's LLM, reachable over an OpenAI-compatible API

Further reading: [Agentverse documentation](https://docs.agentverse.ai) ·
[Fetch.ai documentation](https://fetch.ai/docs) ·
[uAgents framework](https://github.com/fetchai/uAgents) ·
[ASI:One documentation](https://docs.asi1.ai)

---

## License

[Apache 2.0](LICENSE). © Fetch.ai Limited.
