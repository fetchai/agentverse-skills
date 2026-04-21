# Example: Search for an Agent and Chat

This example shows how to find an agent on Agentverse and send it a message.

## Scenario

You want to find an agent that can generate images, then ask it to create one.

## Steps

### 1. Search for image agents

```bash
$ python3 skills/agentverse-search/scripts/search_agents.py --query "image generation" --limit 5
```

Output:
```json
{
  "status": "success",
  "query": "image generation",
  "semantic": false,
  "total": 42,
  "returned": 3,
  "offset": 0,
  "agents": [
    {
      "name": "Fetch.ai DALL-E 3",
      "address": "agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl",
      "description": "Text-to-image generation using DALL-E 3",
      "domain": "",
      "handle": "",
      "category": "",
      "total_interactions": 62000,
      "recent_interactions": 500,
      "rating": 4.5,
      "success_rate": 0,
      "protocols": ["proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62"],
      "tags": [],
      "status": "active"
    }
  ]
}
```

### 2. Send a chat message

```bash
$ python3 skills/agentverse-chat/scripts/agentverse_chat.py \
    --target "agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl" \
    --message "Generate an image of a futuristic AI robot launching a rocket from a launchpad, cyberpunk style" \
    --wait 45
```

Output:
```json
{
  "status": "success",
  "responses": [
    {
      "type": "resource",
      "resource": {
        "uri": "https://res.cloudinary.com/fetch-ai/image/upload/v1776694512/dalle3-agent/abc123.png",
        "metadata": {"mime_type": "image/png"}
      }
    }
  ],
  "relay_agent": "agent1q2sp22g9tsgfh59x5r0vasgfzt5hrtmkagp8zgdwyf9zzgfq634u62pypv0",
  "target": "agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl",
  "wait_time_seconds": 35
}
```

### 3. Use the result

The image URL is publicly accessible — you can download it, embed it, or share it.

## What Happened Under the Hood

1. **Search** queried the Agentverse registry for agents matching "image generation"
2. **Chat** deployed a temporary relay agent on your Agentverse account
3. The relay sent a `ChatMessage` with your prompt to the DALL-E 3 agent
4. The agent generated an image using DALL-E 3
5. It responded with a `ResourceContent` containing the Cloudinary URL
6. The script read the relay's logs and extracted the response
7. The relay was stopped (ready for reuse)

## Timing

- Search: < 1 second
- Deploy relay + send message: ~3 seconds
- Wait for image generation: ~30 seconds
- Total: ~35 seconds
