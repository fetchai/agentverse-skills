# Example: Multi-Agent Workflow

Chain multiple Agentverse skills together for complex workflows.

## Scenario: Research + Summarize + Visualize

Ask ASI:One to research a topic, then use an image agent to visualize it.

### Step 1: Research with ASI:One

```bash
$ python3 skills/asi1-chat/scripts/asi1_chat.py \
    --prompt "Describe the most interesting visual concept for an AI agent marketplace. Be vivid and specific in 2 sentences." \
    --model asi1-mini
```

Output:
```json
{
  "status": "success",
  "model": "asi1-mini",
  "response": "Imagine a vast crystalline bazaar floating in cyberspace, where holographic AI agents of every shape — from geometric fractals to humanoid advisors — hover at translucent stalls, each radiating data streams that connect to seekers below. The marketplace pulses with bioluminescent energy as transactions flow like rivers of light between buyers and autonomous digital merchants."
}
```

### Step 2: Generate the Image

```bash
$ python3 skills/agentverse-image-gen/scripts/generate_image.py \
    --prompt "A vast crystalline bazaar floating in cyberspace, holographic AI agents of every shape hover at translucent stalls, radiating data streams, bioluminescent energy, rivers of light, digital art" \
    --wait 60
```

Output:
```json
{
  "status": "success",
  "image_url": "https://res.cloudinary.com/fetch-ai/image/upload/...",
  "elapsed_seconds": 34.2
}
```

## Scenario: Find and Inspect, Then Chat

### Step 1: Search
```bash
$ python3 skills/agentverse-search/scripts/search_agents.py --query "weather data"
```

### Step 2: Inspect the best match
```bash
$ python3 skills/agentverse-inspect/scripts/inspect_agent.py --agent agent1q...
```

### Step 3: Chat
```bash
$ python3 skills/agentverse-chat/scripts/agentverse_chat.py \
    --target agent1q... \
    --message "What's the weather in London right now?"
```

## Scenario: Deploy, Test, Monitor

### Step 1: Deploy your agent
```bash
$ python3 skills/agentverse-deploy/scripts/deploy_agent.py --name "my-bot" --file bot.py --start
```

### Step 2: Send it a test message
```bash
$ python3 skills/agentverse-chat/scripts/agentverse_chat.py \
    --target DEPLOYED_AGENT_ADDRESS \
    --message "Test message" \
    --wait 15
```

### Step 3: Check logs
```bash
$ python3 skills/agentverse-manage/scripts/manage_agents.py logs --agent DEPLOYED_AGENT_ADDRESS
```

### Step 4: List all your agents
```bash
$ python3 skills/agentverse-manage/scripts/manage_agents.py list
```

## Automation Tips

- All scripts output JSON — pipe to `jq` for field extraction
- Chain with: `IMAGE_URL=$(python3 generate_image.py ... | jq -r .image_url)`
- Error handling: check `.status` field in output
- Timeouts: different agents need different `--wait` values
