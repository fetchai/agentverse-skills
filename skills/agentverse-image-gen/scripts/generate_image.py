#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2026 Fetch.ai Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
generate_image.py — Generate images using Agentverse AI image generation agents.

Sends a text prompt to an image generation agent and returns the generated image URL.
If no agent is specified, searches for available image generation agents automatically.

Usage:
    python3 generate_image.py --prompt "A dragon breathing fire"
    python3 generate_image.py --prompt "Cyberpunk city" --agent agent1q...
    python3 generate_image.py --prompt "A cat in space" --wait 90
    python3 generate_image.py --search  # List available image gen agents

Requirements:
    - requests library (pip install requests)
    - AGENTVERSE_API_KEY environment variable set

Output:
    JSON to stdout: {"status": "success", "image_url": "...", "metadata": {...}}
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

try:
    import requests
except ImportError:
    print(
        json.dumps({"status": "error", "error": "requests library not installed. Run: pip install requests"}),
        file=sys.stdout,
    )
    sys.exit(1)


BASE_URL = "https://agentverse.ai/v1/hosting/agents"
SEARCH_URL = "https://agentverse.ai/v1/search/agents"

# Known working image generation agents.
# Use the official Fetch.ai DALL-E 3 agent (verified active in Almanac).
# If this agent becomes unavailable, run `--search` to discover active alternatives.
DEFAULT_IMAGE_AGENT = "agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl"  # Fetch.ai DALL-E 3
RELAY_AGENT_NAME = "agentverse-skills-relay"


def log(msg: str) -> None:
    """Print log message to stderr."""
    print(f"[agentverse-image-gen] {msg}", file=sys.stderr)


def get_api_key() -> str:
    """Get Agentverse API key from environment."""
    key = os.environ.get("AGENTVERSE_API_KEY", "").strip()
    if not key:
        print(
            json.dumps({
                "status": "error",
                "error": "AGENTVERSE_API_KEY environment variable not set. "
                         "Get your key at https://agentverse.ai/profile/api-keys"
            }),
            file=sys.stdout,
        )
        sys.exit(1)
    return key


def headers(api_key: str) -> dict:
    """Standard headers."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def search_image_agents(api_key: str) -> list:
    """Search for image generation agents on Agentverse."""
    queries = ["image generation", "generate image", "text to image", "AI art"]
    all_agents = {}

    for query in queries:
        try:
            r = requests.post(
                SEARCH_URL,
                headers=headers(api_key),
                json={
                    "search_text": query,
                    "semantic_search": False,
                    "limit": 20,
                    "offset": 0,
                    "sort": "interactions",
                    "direction": "desc",
                    "cutoff": "balanced",
                    "source": "agentverse",
                },
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                for agent in data.get("agents", []):
                    addr = agent.get("address", "")
                    if addr and addr not in all_agents:
                        all_agents[addr] = {
                            "name": agent.get("name", "Unknown"),
                            "address": addr,
                            "description": agent.get("short_description", "")[:200],
                            "interactions": agent.get("total_interactions", 0),
                            "rating": agent.get("rating", 0),
                        }
        except Exception:
            continue

    # Sort by interactions (most popular first)
    agents = sorted(all_agents.values(), key=lambda x: x["interactions"], reverse=True)
    return agents


def find_relay_agent(api_key: str) -> Optional[str]:
    """Find an existing relay agent."""
    try:
        r = requests.get(BASE_URL, headers=headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()
        agents = data.get("items", data) if isinstance(data, dict) else data
        for agent in agents:
            if agent.get("name") == RELAY_AGENT_NAME:
                return agent.get("address")
        # Fallback: use any stopped agent
        for agent in agents:
            if not agent.get("running"):
                return agent.get("address")
    except Exception:
        pass
    return None


def create_relay_agent(api_key: str) -> Optional[str]:
    """Create a new relay agent."""
    try:
        r = requests.post(
            BASE_URL,
            headers=headers(api_key),
            json={"name": RELAY_AGENT_NAME},
            timeout=30,
        )
        if r.status_code in (200, 201):
            return r.json().get("address")
    except Exception:
        pass
    return None


def build_image_gen_code(target_address: str, prompt: str) -> str:
    """Build hosted agent code that sends an image generation request."""
    escaped_prompt = prompt.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    return f'''from datetime import datetime
from uuid import uuid4
from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage, ChatAcknowledgement, TextContent, chat_protocol_spec
)

TARGET = "{target_address}"
PROMPT = "{escaped_prompt}"

protocol = Protocol(spec=chat_protocol_spec)

@agent.on_event("startup")
async def send_prompt(ctx: Context):
    ctx.logger.info("IMAGE_STATUS:sending_prompt")
    await ctx.send(TARGET, ChatMessage(
        timestamp=datetime.now(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=PROMPT)],
    ))
    ctx.logger.info("IMAGE_STATUS:prompt_sent")

@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info("IMAGE_STATUS:ack_received")

@protocol.on_message(ChatMessage)
async def handle_response(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info("IMAGE_STATUS:response_received")
    for item in msg.content:
        try:
            item_dict = item.dict() if hasattr(item, "dict") else str(item)
            ctx.logger.info("RESULT:" + str(item_dict))
        except Exception as e:
            ctx.logger.info("RESULT:" + repr(item))

agent.include(protocol, publish_manifest=True)
'''


def generate_image(api_key: str, prompt: str, target: str, wait: int, relay: Optional[str]) -> dict:
    """Execute the image generation workflow."""
    # Find or create relay
    if relay:
        agent_address = relay
    else:
        agent_address = find_relay_agent(api_key)
        if not agent_address:
            agent_address = create_relay_agent(api_key)
        if not agent_address:
            return {"status": "error", "error": "Could not find or create relay agent. Specify --relay."}

    log(f"Using relay agent: {agent_address}")
    log(f"Target image agent: {target}")
    log(f"Prompt: {prompt[:80]}...")

    # Stop, upload code, start
    try:
        requests.post(f"{BASE_URL}/{agent_address}/stop", headers=headers(api_key), timeout=30)
    except Exception:
        pass
    time.sleep(2)

    code = build_image_gen_code(target, prompt)
    files = [{"language": "python", "name": "agent.py", "value": code}]
    payload = {"code": json.dumps(files)}

    try:
        r = requests.put(
            f"{BASE_URL}/{agent_address}/code",
            headers=headers(api_key),
            json=payload,
            timeout=30,
        )
        if r.status_code not in (200, 201, 204):
            return {"status": "error", "error": f"Code upload failed: {r.status_code}"}
    except Exception as e:
        return {"status": "error", "error": f"Code upload error: {e}"}

    time.sleep(1)

    try:
        r = requests.post(f"{BASE_URL}/{agent_address}/start", headers=headers(api_key), timeout=30)
        if r.status_code not in (200, 201):
            return {"status": "error", "error": f"Agent start failed: {r.status_code}"}
    except Exception as e:
        return {"status": "error", "error": f"Agent start error: {e}"}

    # Wait and poll for results
    log(f"Waiting up to {wait}s for image generation...")
    elapsed = 0
    poll_interval = 5
    results = []

    while elapsed < wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        try:
            r = requests.get(
                f"{BASE_URL}/{agent_address}/logs/latest",
                headers=headers(api_key),
                timeout=30,
            )
            if r.status_code == 200:
                logs = r.json() if isinstance(r.json(), list) else []
                sorted_logs = sorted(logs, key=lambda x: x.get("log_timestamp", ""))
                for entry in sorted_logs:
                    msg = entry.get("log_entry", "")
                    if msg.startswith("RESULT:"):
                        results.append(msg[7:])
                if results:
                    log(f"Got response after {elapsed}s")
                    break
        except Exception:
            pass

        if elapsed % 15 == 0:
            log(f"  ...waiting ({elapsed}/{wait}s)")

    # Stop agent
    try:
        requests.post(f"{BASE_URL}/{agent_address}/stop", headers=headers(api_key), timeout=30)
    except Exception:
        pass

    # Parse results
    if not results:
        return {
            "status": "timeout",
            "error": f"No response received within {wait}s. Image generation may take longer — try increasing --wait.",
            "relay_agent": agent_address,
            "target": target,
        }

    # Extract image URL from results
    image_url = None
    metadata = {}
    all_content = []

    for result_str in results:
        try:
            cleaned = result_str.replace("'", '"').replace("None", "null").replace("True", "true").replace("False", "false")
            result_obj = json.loads(cleaned)
            all_content.append(result_obj)

            # Check for ResourceContent (image)
            if isinstance(result_obj, dict):
                resource = result_obj.get("resource", {})
                if resource and resource.get("uri"):
                    image_url = resource["uri"]
                    metadata = resource.get("metadata", {})
                # Also check nested structures
                if result_obj.get("type") == "resource":
                    res = result_obj.get("resource", {})
                    if res.get("uri"):
                        image_url = res["uri"]
                        metadata = res.get("metadata", {})
        except (json.JSONDecodeError, ValueError):
            all_content.append(result_str)
            # Try to find URL in raw string
            if "http" in result_str and ("cloudinary" in result_str or "imgur" in result_str or ".png" in result_str or ".jpg" in result_str):
                # Extract URL from string
                for part in result_str.split():
                    if part.startswith("http"):
                        image_url = part.strip("'\"(),")
                        break

    output = {
        "status": "success",
        "prompt": prompt,
        "target_agent": target,
        "relay_agent": agent_address,
        "wait_time_seconds": elapsed,
        "content": all_content,
    }

    if image_url:
        output["image_url"] = image_url
        output["metadata"] = metadata

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Agentverse AI agents.",
        epilog="Example: python3 generate_image.py --prompt 'A dragon breathing fire'",
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Image generation prompt (text description)",
    )
    parser.add_argument(
        "--agent", "-a",
        default=DEFAULT_IMAGE_AGENT,
        help=f"Target image generation agent address (default: Fetch.ai DALL-E 3 {DEFAULT_IMAGE_AGENT[:20]}...)",
    )
    parser.add_argument(
        "--wait", "-w", type=int, default=60,
        help="Max seconds to wait for image generation (default: 60)",
    )
    parser.add_argument(
        "--relay",
        help="Specific relay agent address to use (optional)",
    )
    parser.add_argument(
        "--search", action="store_true",
        help="Search for available image generation agents instead of generating",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging to stderr",
    )

    args = parser.parse_args()

    if not args.verbose:
        global log
        log = lambda msg: None  # noqa: E731

    api_key = get_api_key()

    if args.search:
        agents = search_image_agents(api_key)
        result = {
            "status": "success",
            "query": "image generation",
            "total": len(agents),
            "agents": agents,
            "recommended": DEFAULT_IMAGE_AGENT,
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if not args.prompt:
        parser.error("--prompt is required (unless using --search)")
        sys.exit(1)

    result = generate_image(
        api_key=api_key,
        prompt=args.prompt,
        target=args.agent,
        wait=args.wait,
        relay=args.relay,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
