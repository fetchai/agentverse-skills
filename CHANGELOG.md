# Changelog

All notable changes to this project will be documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [Unreleased]

### Fixed

- **`agentverse-memory` skill — corrected to match LIVE production** (skill `version` → 1.1.0). Several `memory_client.py` tool names were stale and returned `-32601 unknown tool`; they now match the live 35-tool MCP API: `memory_query_episodes`→`memory_search_episodes`, `memory_list_episodes`→`memory_get_episodes`, `memory_store_fact`→`memory_graph_add_triple`, `memory_query_facts`→`memory_query_graph`, `memory_execute_procedure_lookup`→`memory_match_procedure`, `memory_stats`→`memory_get_stats`. Also fixed argument names: `store-procedure` now sends `name` (was `goal`), `lookup-procedure` sends `task` (was `goal`), `traverse-graph` sends `start_id` (was `seed_concept`). Verified end-to-end against prod (`https://am-server-jbneh74b5q-uc.a.run.app`).
- **`agentverse-memory` skill — key-mint and pricing docs corrected.** The free-key response field is `key` (not `api_key`) and the limit is `monthly_op_limit` (not `ops_per_month`); every example now reads the real shape. Pricing table corrected to canonical tiers: Explorer free **50,000 ops/mo** (was 10,000), Builder $19/mo **500,000 ops/mo** (was 100,000), Pro $99/mo **5,000,000 ops/mo** (was "Unlimited"), plus a new **Enterprise** (Custom: SLA, SOC 2, BYOC). Graph-at-every-tier (incl. free) framing kept.

### Changed

- **`agentverse-memory` skill — retrieval, pheromone, MCP-spec, and SDK clarifications:**
  - Retrieval description corrected to the live behavior: default **hybrid** retrieval (TF-IDF lexical ∪ dense `text-embedding-3-small`, fused via Reciprocal Rank Fusion, k=60) — replaces the inaccurate "BM25 + HNSW + pheromone reranking". `memory_search_episodes` now documents `query`/`limit`/`use_hybrid`/`use_pheromone`/`max_content_chars` and reports `"retrieval":"hybrid"|"tfidf"`; `memory_client.py query-episodes` gained `--no-hybrid` / `--use-pheromone` flags. Zero-LLM-write ($0 ingest, <5ms writes) moat kept front and center.
  - Pheromone reframed as **opt-in / default off** (warm-cache, repeated-access, and cross-agent multi-agent workloads) rather than a default per-query reranker.
  - MCP protocol section reflects the completed MCP-spec migration: results now include `structuredContent` + `isError`; tool-execution failures are reported **in-band** (`isError:true` + `structuredContent.error{code,type,message}`) rather than as top-level JSON-RPC errors; five read tools declare `outputSchema`; the server negotiates protocol version up to RC `2026-07-28` (default `2025-11-25`). `memory_client.py` now surfaces in-band errors and prefers `structuredContent`.
  - **SDK not-yet-published clarification:** PyPI `agentverse-memory` and npm `@fetchai/agentverse-memory` are not live yet — onboarding now leads with the bundled `scripts/memory_client.py` and raw curl/MCP, with a "SDK coming soon" note instead of `pip install agentverse-memory`.
  - Documentation links repointed to verified-200 URLs (`https://fetchai.github.io/agentverse-memory/` and `/docs/`, `/docs/mcp`, `/docs/python-sdk`); removed dead `agentverse.ai/docs/*`, `/docs/api-reference`, and unpublished package/repo links.

### Added

- **`agentverse-memory` skill — complete parameter reference for all 35 MCP tools** (skill `version` → 1.2.0). Added a new **Tool Parameter Reference (all 35 tools)** section to `SKILL.md` documenting every tool's arguments (type, required/optional, default, one-line description), grouped by memory type (Episodic, Entity, Graph Operations, Graph Direct, Procedural, Working, Pheromone, Shared, Utility). Previously only `memory_search_episodes` had a full parameter spec — the other 34 tools were effectively uncallable for external agents because the `agentverse-memory` repo is private and the public skill is the only readable reference. Parameters were sourced directly from the live server handlers (`am-server/src/mcp.rs`) and agree with the `inputSchema` definitions now published via `tools/list`. Also clarifies that `agent_id` is derived from the API key (not a tool argument) and that `memory_find_path` (A*) is tier-gated.
- **`public_url` field in image responses** ([#31](https://github.com/fetchai/agentverse-skills/issues/31)): When an image agent returns an `agent-storage://` URI, `generate_image.py` now also includes `public_url` — a direct HTTPS URL that can be opened in a browser or downloaded with `requests.get()`. `agentverse_chat.py` similarly enriches resource responses with `public_url` when present.
- **Windows / PowerShell documentation** ([#31](https://github.com/fetchai/agentverse-skills/issues/31)): Added full Windows setup guide to `README.md` (new [Windows / PowerShell](#-windows--powershell) section), PowerShell equivalents to `docs/authentication.md`, and a dedicated Windows troubleshooting section to `docs/troubleshooting.md`. Covers `$env:VAR` syntax, `py` launcher, backtick line continuation, and persistent env var setup.

### Changed

- **`asi1-chat`**: Default model changed from `asi1-mini` to `asi1` — aligns with Fetch.ai Innovation Labs docs and community usage. `asi1-mini` remains available via `--model asi1-mini` for lower-latency use cases.
- **All docs**: Updated examples, API reference, and authentication guide to use `asi1` as the default model.

### Improved

- **`docs/troubleshooting.md`**: Expanded timeout guidance with a cheat sheet of recommended `--wait` values per operation, retry advice, and streaming tips.

---

## [1.1.0] — 2026-04-21

### Fixed

- **`search_agents.py`**: `--protocol` flag now correctly uses `filters.protocol_digest` format instead of the rejected `protocol` field — fixes 422 error ([#2](https://github.com/fetchai/agentverse-skills/issues/2), [PR #11](https://github.com/fetchai/agentverse-skills/pull/11))
- **`search_agents.py`**: Search endpoint corrected from the non-existent `GET /v1/almanac/search` to the working `POST /v1/almanac/agents/search` — fixes 404 ([#1](https://github.com/fetchai/agentverse-skills/issues/1), [PR #11](https://github.com/fetchai/agentverse-skills/pull/11))
- **`generate_image.py`**: Default image agent updated from stale nano-banana address to the verified Fetch.ai DALL-E 3 agent (`agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl`) — fixes perpetual timeout ([#3](https://github.com/fetchai/agentverse-skills/issues/3), [PR #11](https://github.com/fetchai/agentverse-skills/pull/11))
- **`generate_image.py`**: Polling now waits for an actual image URL, not just the initial text acknowledgment — fixes cases where only a text ACK was returned and the script exited without the image ([#4](https://github.com/fetchai/agentverse-skills/issues/4), [PR #12](https://github.com/fetchai/agentverse-skills/pull/12))
- **All scripts**: Python 3.8 compatibility restored — replaced `str | None` union syntax with `Optional[str]` from `typing` ([#5](https://github.com/fetchai/agentverse-skills/issues/5), [PR #11](https://github.com/fetchai/agentverse-skills/pull/11))
- **`agentverse_chat.py`**: `extract_results()` now handles apostrophes and other special characters safely — was silently returning empty results on certain agent responses ([#6](https://github.com/fetchai/agentverse-skills/issues/6), [PR #11](https://github.com/fetchai/agentverse-skills/pull/11))
- **`deploy_agent.py`**: Removed incorrect hardcoded "max 8 agents" error message — actual Agentverse limit is higher ([#7](https://github.com/fetchai/agentverse-skills/issues/7), [PR #11](https://github.com/fetchai/agentverse-skills/pull/11))

### Added

- **`manage_agents.py`**: New `restart` command — stops and restarts a named hosted agent in one call ([#9](https://github.com/fetchai/agentverse-skills/issues/9), [PR #13](https://github.com/fetchai/agentverse-skills/pull/13))
- **`agentverse_chat.py`**: New `--start-session` flag — sends a `StartSessionContent` message before the main payload for agents that require session initiation ([#10](https://github.com/fetchai/agentverse-skills/issues/10), [PR #13](https://github.com/fetchai/agentverse-skills/pull/13))
- **`tests/test_integration.py`**: Live integration tests covering search, manage, ASI:One, and inspect skills — real API calls, skipped gracefully if credentials absent ([#8](https://github.com/fetchai/agentverse-skills/issues/8), [PR #13](https://github.com/fetchai/agentverse-skills/pull/13))
- **`.github/workflows/integration.yml`**: CI workflow for integration tests — runs on push to `main` (when enabled) and on manual dispatch, non-blocking (`continue-on-error: true`) ([#8](https://github.com/fetchai/agentverse-skills/issues/8), [PR #13](https://github.com/fetchai/agentverse-skills/pull/13))

---

## [1.0.0] — 2026-04-20

### Added

- Initial release with 7 skills:
  - `agentverse-search` — search the Agentverse agent registry
  - `agentverse-chat` — send messages to any Agentverse agent
  - `agentverse-image-gen` — generate images via hosted agents
  - `agentverse-manage` — manage hosted agents (list, start, stop)
  - `agentverse-inspect` — inspect agent metadata and Almanac status
  - `agentverse-deploy` — deploy Python code as a hosted agent
  - `asi1-chat` — query the ASI:One LLM
- `SKILL.md` definitions for all 7 skills (SKILL.md format)
- `AGENTS.md` — technical guide for AI agents working on this repo
- `examples/` — 4 worked examples with real CLI outputs
- `docs/` — API reference, authentication guide, troubleshooting
- `tests/` — syntax and SKILL.md validation in CI
- `.github/workflows/test.yml` — CI on push/PR (Python 3.8/3.10/3.12 matrix)
- `package.json` for npm discoverability

---

[Unreleased]: https://github.com/fetchai/agentverse-skills/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/fetchai/agentverse-skills/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/fetchai/agentverse-skills/releases/tag/v1.0.0
