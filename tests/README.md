# Tests

## Unit Tests (`test_unit.py`)

Offline tests for parsing logic, validation, and utility functions. **No API
credentials or network access needed.**

```bash
python3 tests/test_unit.py
# or
pytest tests/test_unit.py -v
```

| Test Class | Checks |
|------------|--------|
| `TestParseResultEntry` | JSON, Python repr, UUID stripping, apostrophes, raw fallback |
| `TestExtractResults` | RESULT: extraction, ordering, empty cases |
| `TestExtractStatus` | Status extraction, custom prefix, unknown default |
| `TestIsRelayAgent` | Relay name prefix matching, edge cases |

## Integration Tests (`test_integration.py`)

Live API tests that exercise the full skill scripts end-to-end.

### Requirements

- `AGENTVERSE_API_KEY` environment variable — Agentverse JWT bearer token
  - Get yours at: https://agentverse.ai/profile/api-keys
- `ASI_ONE_API_KEY` environment variable — for ASI:One tests (optional)
  - Get yours at: https://asi1.ai
- Python 3.8+ with `requests` installed

### Running

```bash
# Set credentials
export AGENTVERSE_API_KEY="eyJ..."
export ASI_ONE_API_KEY="sk_..."   # optional

# Run all integration tests
python3 tests/test_integration.py

# Or with pytest (verbose)
pip install pytest
pytest tests/test_integration.py -v

# Run only unit tests (fast, no API needed)
pytest tests/test_unit.py -v
```

### What Is Tested

| Test | Checks |
|------|--------|
| **Search** | |
| `TestSearchAgents.test_keyword_search_returns_results` | Search returns ≥1 agent for "image generation" |
| `TestSearchAgents.test_tags_endpoint_returns_list` | Tags endpoint returns non-empty list |
| `TestSearchAgents.test_protocol_filter_no_error` | `--protocol` flag no longer returns 422 |
| **Manage** | |
| `TestManageAgents.test_list_agents_succeeds` | List hosted agents returns valid response |
| `TestManageAgents.test_list_running_only` | `--running` flag returns subset |
| `TestManageCleanup.test_cleanup_returns_structured_output` | `cleanup` subcommand returns structured JSON |
| **ASI:One** | |
| `TestASI1Chat.test_basic_prompt_returns_text` | ASI:One mini returns non-empty response |
| **Inspect** | |
| `TestInspectAgent.test_inspect_known_agent` | Almanac lookup returns address |
| `TestInspectAgent.test_recent_agents` | Recent agents list returns results |
| **Deploy** | |
| `TestDeployAgent.test_deploy_inline_code` | Deploy inline code, verify in list, delete |
| **Chat** | |
| `TestChatAgent.test_chat_returns_structured_output` | Chat returns structured JSON (success or timeout) |
| `TestChatAgent.test_chat_timeout_includes_debug_info` | Timeout includes log_entries and last_status |
| **Image Gen** | |
| `TestImageGenAgent.test_search_image_agents` | `--search` returns image generation agents |
| `TestImageGenAgent.test_image_gen_returns_structured_output` | Image gen returns structured JSON |

### CI Notes

Integration tests run in GitHub Actions when `AGENTVERSE_API_KEY` is available
as a repository secret. They are non-blocking (`continue-on-error: true`) to
avoid failing PRs due to transient API issues.

Chat and image-gen tests use `--cleanup` to avoid accumulating relay agents.
Deploy tests delete the test agent in `tearDown`.
