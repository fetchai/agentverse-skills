# Hosted Agent Gotchas — Hard-Won Lessons

These are issues we encountered while building and testing the Agentverse hosting API integration. They're not well-documented elsewhere.

## 1. Code Upload Format

The `/v1/hosting/agents/{address}/code` endpoint expects:

```json
{
  "code": "[{\"language\":\"python\",\"name\":\"agent.py\",\"value\":\"your_code_here\"}]"
}
```

**The `code` field is a JSON STRING, not a JSON array.** You must `json.dumps()` the file list:

```python
import json

code_content = "..."  # Your Python source
files = [{"language": "python", "name": "agent.py", "value": code_content}]
payload = {"code": json.dumps(files)}

# WRONG: {"code": [{"language": "python", ...}]}  ← This fails silently
# RIGHT: {"code": "[{\"language\": \"python\", ...}]"}  ← JSON string of list
```

## 2. No Agent() Constructor

In the hosted environment, `agent` is a global variable pre-created by the platform:

```python
# WRONG — will crash:
from uagents import Agent
agent = Agent(name="my-agent", seed="...")
agent.run()

# RIGHT — agent already exists:
from uagents import Context

@agent.on_event("startup")
async def start(ctx: Context):
    ctx.logger.info("Started!")
```

## 3. No agent.run()

The platform manages the agent lifecycle. Calling `.run()` will either:
- Crash with "event loop already running"
- Block indefinitely
- Cause undefined behavior

Just define your handlers and `agent.include()` your protocols.

## 4. F-String Parser Bug

Avoid list comprehensions inside f-strings in hosted code:

```python
# WRONG — parser error in hosted env:
ctx.logger.info(f"Items: {[str(x) for x in items]}")

# RIGHT — compute first:
items_str = str([str(x) for x in items])
ctx.logger.info("Items: " + items_str)
```

## 5. Logging is Your Only Output

- No `print()` output visible
- No `sys.stdout` / `sys.stderr` access
- Only `ctx.logger.info()`, `ctx.logger.warning()`, `ctx.logger.error()`
- Read logs via `GET /v1/hosting/agents/{address}/logs/latest`

## 6. Agent State Can Get Stuck

If an agent fails during startup or has a compilation error:
- It may show as "running" but not actually process messages
- Stopping and restarting may not help
- **Fix**: Use a different agent (create new, or use another from your list)

## 7. Available Libraries

The hosted environment has:
- Python standard library (full)
- `uagents` (latest)
- `uagents_core` (latest)
- `requests`
- `cosmpy` (for wallet/transaction operations)

**NOT available**: `numpy`, `pandas`, `torch`, `PIL`, etc. For ML workloads, call external APIs.

## 8. Startup Event Fires Once

`@agent.on_event("startup")` fires exactly once when the agent starts. If you need periodic behavior, use:

```python
@agent.on_interval(period=60.0)  # Every 60 seconds
async def periodic(ctx: Context):
    pass
```

## 9. Message Size Limits

- Keep messages under ~1MB
- For large payloads, use URLs (like Cloudinary) rather than inline data
- Code upload: keep source under 100KB

## 10. Polling for Responses

There's no webhook/callback mechanism. To get responses:

1. Start your relay agent
2. Wait (sleep/poll)
3. Read logs
4. Parse RESULT: prefixed entries

The pattern:
```python
import time
time.sleep(wait_seconds)
logs = requests.get(f"{BASE}/{addr}/logs/latest", headers=headers).json()
results = [e["log_entry"][7:] for e in logs if e.get("log_entry","").startswith("RESULT:")]
```

## 11. Agent Address Format

- Format: `agent1q...` (bech32 encoded)
- Length: typically 63-66 characters
- Deterministic: derived from the agent's seed phrase
- Hosted agents: address assigned by platform (you can't choose it)
