---
name: agentverse-image-gen
description: >
  Generate images using AI agents on Fetch.ai's Agentverse. Sends a text prompt
  to an image generation agent and returns the generated image URL.
  Handles agent discovery, relay deployment, and response parsing automatically.
  Requires AGENTVERSE_API_KEY env var. Use when asked to generate, create, or
  make an image via Agentverse.
license: Apache-2.0
compatibility: Python 3.8+, network access, AGENTVERSE_API_KEY env var
metadata:
  version: "1.0.0"
  author: "Fetch.ai"
  last-updated: "2026-04-20"
allowed-tools: Read Bash(python3 *) Bash(curl *) Bash(pip install requests)
---

# Agentverse Image Generation

## Overview

Generate images by sending text prompts to AI image generation agents on Agentverse. Returns a public URL to the generated image. Fully automatic — discovers agents, deploys relay, sends prompt, returns result.

## When to Use

- User asks to "generate an image using Agentverse"
- User asks to "use an AI agent to create a picture"
- User wants AI-generated art via the Fetch.ai agent network
- User says "make me an image of..." in context of Agentverse

## Prerequisites

- `AGENTVERSE_API_KEY` environment variable set
- Python 3.8+ with `requests`

## Quick Steps

### 1. Generate an image
```bash
python3 scripts/generate_image.py \
  --prompt "A futuristic AI robot launching a rocket from a launchpad, cyberpunk style, neon colors" \
  --wait 60
```

### 2. With a specific agent
```bash
python3 scripts/generate_image.py \
  --prompt "A dragon made of circuit boards on a Tokyo rooftop at sunset" \
  --agent "agent1qdynamic8lgnax37n20296xr4kcfllahlnse7gy5mrkdt4q9v9h06qkmclkl" \
  --wait 60
```

### 3. Parse the result
```json
{
  "status": "success",
  "prompt": "A dragon made of circuit boards...",
  "image_url": "https://res.cloudinary.com/fetch-ai/image/upload/v1776700090/dalle3-agent/0932ec14-...",
  "metadata": {},
  "target_agent": "agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl",
  "relay_agent": "agent1q...",
  "wait_time_seconds": 35,
  "all_responses": [{"type": "text", "text": "Generating..."}, "..."]
}
```

## How It Works

1. **Discover agent**: If no `--agent` specified, searches for image generation agents
2. **Deploy relay**: Creates/reuses a hosted agent as a message relay
3. **Send prompt**: Sends `ChatMessage` with your prompt as `TextContent`
4. **Wait for generation**: Image agents typically take 20-45 seconds
5. **Extract URL**: Parses `ResourceContent` from response logs
6. **Return**: Outputs JSON with the image URL

## Default Agent

If you don't specify `--agent`, the script uses the well-known **Fetch.ai DALL-E 3** image agent:
```
agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl
```

This agent generates images using DALL-E 3 and returns them as Cloudinary URLs.

## Timing

- **ACK**: ~1 second (confirms message received)
- **Image generation**: 20-45 seconds (model inference + upload)
- **Recommended --wait**: 60 seconds (safe margin)

## Edge Cases

- **Timeout**: If no image after 60s, the agent may be overloaded — retry later
- **Text response instead of image**: Some agents respond with text first, then image. Increase `--wait`
- **Agent offline**: Use `agentverse-search` to find alternative image agents
- **Large prompts**: Keep prompts under 500 characters for best results

## Example Prompts That Work Well

- "A futuristic AI robot launching a rocket, cyberpunk style"
- "A cat astronaut floating in space with Earth in the background"
- "A dragon made of circuit boards standing on a Tokyo rooftop at sunset"
- "An underwater city with bioluminescent buildings and fish"

## References

- Uses `agentverse-chat` pattern internally
- [Agentverse agents directory](https://agentverse.ai/agents)
