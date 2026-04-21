# Integration Tests

Live integration tests for agentverse-skills. These tests make real API calls to
Agentverse and ASI:One to verify the skills work end-to-end.

## Requirements

- `AGENTVERSE_API_KEY` environment variable — Agentverse JWT bearer token
  - Get yours at: https://agentverse.ai/profile/api-keys
- `ASI_ONE_API_KEY` environment variable — for ASI:One tests (optional)
  - Get yours at: https://asi1.ai
- Python 3.8+ with `requests` installed

## Running

```bash
# Set credentials
export AGENTVERSE_API_KEY="eyJ..."
export ASI_ONE_API_KEY="sk_..."   # optional

# Run all integration tests
python3 tests/test_integration.py

# Or with pytest (verbose)
pip install pytest
pytest tests/test_integration.py -v
```

## What Is Tested

| Test | Checks |
|------|--------|
| `TestSearchAgents.test_keyword_search_returns_results` | Search returns ≥1 agent for "image generation" |
| `TestSearchAgents.test_tags_endpoint_returns_list` | Tags endpoint returns non-empty list |
| `TestSearchAgents.test_protocol_filter_no_error` | `--protocol` flag no longer returns 422 |
| `TestManageAgents.test_list_agents_succeeds` | List hosted agents returns valid response |
| `TestManageAgents.test_list_running_only` | `--running` flag returns subset |
| `TestASI1Chat.test_basic_prompt_returns_text` | ASI:One mini returns non-empty response |
| `TestInspectAgent.test_inspect_known_agent` | Almanac lookup returns address |
| `TestInspectAgent.test_recent_agents` | Recent agents list returns results |

## CI Notes

These tests run in GitHub Actions when `AGENTVERSE_API_KEY` is available as a
repository secret. They are non-blocking (`continue-on-error: true`) to avoid
failing PRs due to transient API issues.
