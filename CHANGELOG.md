# Changelog

All notable changes to this project will be documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [Unreleased]

### Added

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
