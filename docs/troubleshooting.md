# Troubleshooting

## Common Issues

### "AGENTVERSE_API_KEY not set"

```bash
export AGENTVERSE_API_KEY="your-jwt-token-here"
```

Get a key at: https://agentverse.ai/profile/api-keys

### 401 Unauthorized

Your API key is invalid or expired.
- Check if the key starts with `eyJ` (JWT format)
- Try generating a new key at agentverse.ai
- Ensure no extra whitespace in the env var

### 403 Forbidden

Your key doesn't have permission for this action.
- Some endpoints require specific scopes
- Try generating a new key with full permissions

### Agent Not Responding (Timeout)

1. **Increase wait time**: Try `--wait 90` for image generation
2. **Check agent status**: Is the target agent online?
   ```bash
   python3 scripts/inspect_agent.py --agent agent1q...
   ```
3. **Check your relay logs**: 
   ```bash
   python3 scripts/manage_agents.py logs --agent YOUR_RELAY_ADDR
   ```
4. **Try a different relay agent**: Sometimes agents get stuck
   ```bash
   python3 scripts/manage_agents.py list
   # Pick a different agent or create a new one
   ```

### "Unable to determine message model"

The target agent uses a different protocol version. Solutions:
- Use a different target agent
- Ensure your relay code imports from `uagents_core.contrib.protocols.chat`
- Check the target agent's supported protocols with `agentverse-inspect`

### Code Upload Fails (422 Error)

Check the code format:
```python
import json
files = [{"language": "python", "name": "agent.py", "value": code_string}]
# MUST be json.dumps — NOT a raw list
payload = {"code": json.dumps(files)}
```

### Agent Won't Start (Compilation Error)

Check for:
1. `Agent()` constructor call (remove it — `agent` is pre-created)
2. `agent.run()` call (remove it — platform manages lifecycle)
3. Missing imports (`uagents`, `uagents_core` are available)
4. Syntax errors in f-strings with list comprehensions

Read compilation status:
```bash
python3 scripts/manage_agents.py logs --agent agent1q...
```

### Empty Logs

- Agent may not have started yet (wait 2-3 seconds after start)
- Agent may have crashed on startup (check for compilation errors)
- The startup handler may not have fired (check code logic)

### Rate Limited (429)

Wait 30 seconds and retry. To avoid:
- Don't poll logs more than once per second
- Batch operations where possible
- Use reasonable `--wait` times instead of polling

### Image Generation Returns Text Only

Some agents respond with text (e.g., "Processing your request...") before the image. Solutions:
- Increase `--wait` to 60-90 seconds
- Look for ALL `RESULT:` entries in logs, not just the first one
- The image URL comes as `ResourceContent`, text comes as `TextContent`

### Connection Errors

```
requests.exceptions.ConnectionError
```

- Check internet connectivity
- Agentverse might be temporarily down (check https://status.fetch.ai)
- Retry after 10 seconds

### SSL Certificate Errors

```bash
pip install --upgrade certifi
```

Or on some systems:
```bash
pip install pip-system-certs
```

---

## Debug Mode

Set `--verbose` (where supported) or add logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show full HTTP requests/responses for diagnosis.

---

## Getting Help

- [Fetch.ai Discord](https://discord.gg/fetchai)
- [Agentverse Documentation](https://fetch.ai/docs/guides/agentverse)
- [GitHub Issues](https://github.com/fetchai/agentverse-skills/issues)
