# Example: Image Generation

The simplest way to generate an image via Agentverse.

## One Command

```bash
$ python3 skills/agentverse-image-gen/scripts/generate_image.py \
    --prompt "A dragon made of circuit boards standing on a Tokyo rooftop at sunset, detailed digital art" \
    --wait 60
```

Output:
```json
{
  "status": "success",
  "prompt": "A dragon made of circuit boards standing on a Tokyo rooftop at sunset, detailed digital art",
  "image_url": "https://res.cloudinary.com/fetch-ai/image/upload/v1776700090/dalle3-agent/0932ec14-dragon.png",
  "metadata": {},
  "target_agent": "agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl",
  "relay_agent": "agent1q...",
  "wait_time_seconds": 35,
  "all_responses": ["..."]
}
```

## What This Does Automatically

1. Uses the default Fetch.ai DALL-E 3 image agent (or discovers one via search)
2. Finds/creates a relay agent in your account
3. Sends the prompt as a ChatMessage
4. Waits for the ResourceContent response
5. Extracts and returns the image URL

## Tips for Great Prompts

- Be specific: "cyberpunk style, neon lighting, rain-soaked streets" > "cool looking"
- Mention art style: "digital art", "oil painting", "3D render", "photography"
- Include details: lighting, setting, mood, colors
- Keep under 500 characters for best results

## Real Images Generated During Development

These were actually generated using this exact tooling:

1. **"A futuristic AI robot launching a rocket from a launchpad, cyberpunk style"**
   - 2048×2048, ~30 seconds
   
2. **"A dragon made of circuit boards on a Tokyo skyscraper rooftop at sunset"**
   - 2048×2048, ~32 seconds
