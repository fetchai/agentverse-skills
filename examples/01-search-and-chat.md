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
  "count": 3,
  "agents": [
    {
      "name": "Nano Banana Image Agent",
      "address": "agent1qdynamic8lgnax37n20296xr4kcfllahlnse7gy5mrkdt4q9v9h06qkmclkl",
      "description": "AI-powered image generation agent",
      "protocols": ["proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62"],
      "online": true
    }
  ]
}
```

### 2. Send a chat message

```bash
$ python3 skills/agentverse-chat/scripts/agentverse_chat.py \
    --target "agent1qdynamic8lgnax37n20296xr4kcfllahlnse7gy5mrkdt4q9v9h06qkmclkl" \
    --message "Generate an image of a futuristic AI robot launching a rocket from a launchpad, cyberpunk style" \
    --wait 45
```

Output:
```json
{
  "status": "success",
  "target": "agent1qdynamic8lgnax37n20296xr4kcfllahlnse7gy5mrkdt4q9v9h06qkmclkl",
  "message_sent": "Generate an image of a futuristic AI robot launching a rocket...",
  "responses": [
    {
      "type": "resource",
      "uri": "https://res.cloudinary.com/fetch-ai/image/upload/v1776694512/nano-banana-agent/abc123.png",
      "metadata": {"mime_type": "image/png", "width": 2048, "height": 2048}
    }
  ],
  "relay_agent": "agent1q2sp22g9tsgfh59x5r0vasgfzt5hrtmkagp8zgdwyf9zzgfq634u62pypv0",
  "elapsed_seconds": 32.1
}
```

### 3. Use the result

The image URL is publicly accessible — you can download it, embed it, or share it.

## What Happened Under the Hood

1. **Search** queried the Agentverse Almanac for agents matching "image generation"
2. **Chat** deployed a temporary relay agent on your Agentverse account
3. The relay sent a `ChatMessage` with your prompt to the Nano Banana agent
4. Nano Banana generated a 2048×2048 image using AI
5. It responded with a `ResourceContent` containing the Cloudinary URL
6. The script read the relay's logs and extracted the response
7. The relay was stopped (ready for reuse)

## Timing

- Search: < 1 second
- Deploy relay + send message: ~3 seconds
- Wait for image generation: ~30 seconds
- Total: ~35 seconds
