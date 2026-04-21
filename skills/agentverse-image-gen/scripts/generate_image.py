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
import ast
import json
import os
import re
import sys
import time
from typing import Optional

# Pre-processing regex: strip UUID(...) calls so ast.literal_eval can parse Python reprs
# that include uuid.UUID objects (e.g. from uagents ResourceContent).
_UUID_RE = re.compile(r"\bUUID\('([0-9a-f-]+)'\)")

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

_AGENT_ADDR_RE = re.compile(r"^agent1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{59}$")


def validate_agent_address(address: str, flag_name: str = "--agent") -> None:
    """Validate agent address format (bech32, 65 chars)."""
    if not _AGENT_ADDR_RE.match(address):
        print(json.dumps({
            "status": "error",
            "error": f"Invalid agent address format: {address!r}",
            "hint": "Expected format: agent1q... (65 characters). Use agentverse-search to find addresses.",
        }))
        sys.exit(1)

# Known working image generation agents.
# Use the official Fetch.ai DALL-E 3 agent (verified active in Almanac).
# If this agent becomes unavailable, run `--search` to discover active alternatives.
DEFAULT_IMAGE_AGENT = "agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl"  # Fetch.ai DALL-E 3
RELAY_AGENT_NAME = "agentverse-skills-relay"

# URL patterns that indicate an image has been delivered
_IMAGE_URL_RE = re.compile(
    r'https?://[^\s\'"<>)]+\.(png|jpg|jpeg|webp|gif)(\?[^\s\'"<>)]*)?',
    re.IGNORECASE,
)
_IMAGE_CDN_RE = re.compile(
    r'https?://[^\s\'"<>)]*(?:cloudinary|imgur|i\.ibb\.co|openai\.com/files|'
    r'oaidalleapiprodscus\.blob\.core\.windows\.net|'
    r'cdn\.discordapp\.com)[^\s\'"<>)]*',
    re.IGNORECASE,
)

# Keywords in a text response that indicate a terminal error (no image coming)
_ERROR_KEYWORDS = ("error", "failed", "unable", "cannot", "could not", "sorry")


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


def _parse_result_entry(result_str: str):
    """Parse a RESULT: log entry string into a Python object.

    Uses a multi-stage strategy:
    1. Direct json.loads (handles valid JSON)
    2. ast.literal_eval after stripping UUID(...) calls (handles Python repr with
       apostrophes and uagents UUID fields like resource_id)
    3. Falls back to raw string — never silently drops content
    """
    try:
        return json.loads(result_str)
    except (json.JSONDecodeError, ValueError):
        pass

    # Replace UUID('hex') with just 'hex' so ast.literal_eval can handle it
    cleaned = _UUID_RE.sub(r"'\1'", result_str)
    try:
        return ast.literal_eval(cleaned)
    except (ValueError, SyntaxError):
        pass

    return result_str


def _is_image_uri(uri: str, metadata: dict) -> bool:
    """Return True if a URI appears to be an image (by URL pattern or mime type)."""
    if not uri:
        return False
    # Explicit image mime type in metadata
    mime = metadata.get("mime_type", "")
    if mime.startswith("image/"):
        return True
    # URL pattern matches
    if _IMAGE_URL_RE.search(uri) or _IMAGE_CDN_RE.search(uri):
        return True
    # agent-storage:// URIs always carry images from image-gen agents
    if uri.startswith("agent-storage://"):
        return True
    return False


def _extract_image_url(obj) -> Optional[str]:
    """Try to find an image URL in a parsed result object or raw string.

    Handles:
    - ResourceContent dicts: {"type": "resource", "resource": {"uri": "...", "metadata": {...}}}
    - Flat resource dicts: {"resource": {"uri": "..."}}
    - agent-storage:// URIs (used by hosted Agentverse image agents)
    - CDN / extension-based image URLs in raw strings

    Returns the URI string if an image is detected, None otherwise.
    """
    if isinstance(obj, dict):
        # ResourceContent shape: {"type": "resource", "resource": {"uri": "..."}}
        resource = obj.get("resource", {})
        if not isinstance(resource, dict):
            resource = {}

        uri = resource.get("uri", "")
        metadata = resource.get("metadata", {}) if isinstance(resource.get("metadata"), dict) else {}

        # Also accept top-level type=="resource" even without nested resource key
        if not uri and obj.get("type") == "resource":
            uri = obj.get("uri", "")

        if uri and _is_image_uri(uri, metadata):
            return uri

    # Scan raw string for image-like URLs (covers partially-parsed or repr strings)
    raw = str(obj)

    # agent-storage:// URIs
    m = re.search(r"agent-storage://[^\s'\",)]+", raw)
    if m:
        return m.group(0).strip("'\"(),")

    # Standard http/https image URLs
    for pattern in (_IMAGE_URL_RE, _IMAGE_CDN_RE):
        m = pattern.search(raw)
        if m:
            return m.group(0).strip("'\"(),")

    return None


def _is_text_error(obj) -> bool:
    """Return True if the response is a text error message (no image will follow)."""
    text = ""
    if isinstance(obj, dict):
        if obj.get("type") == "text":
            text = str(obj.get("text", ""))
        elif "text" in obj:
            text = str(obj["text"])
    elif isinstance(obj, str):
        text = obj
    return any(kw in text.lower() for kw in _ERROR_KEYWORDS)


def generate_image(api_key: str, prompt: str, target: str, wait: int, relay: Optional[str]) -> dict:
    """Execute the image generation workflow.

    Key behaviour (fixes issue #4):
    - Does NOT exit on the first text response — many image agents send an
      acknowledgement text ("Generating your image...") before the actual image.
    - Keeps polling until one of:
        (a) A ResourceContent / image URL is found in the responses  ← success
        (b) A text response explicitly signals an error               ← fail-fast
        (c) The --wait timeout is exhausted                           ← timeout
    """
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

    # ------------------------------------------------------------------ #
    # Polling loop — wait for image URL, not just any response            #
    #                                                                     #
    # Image agents typically send TWO responses:                          #
    #   1. Text ACK: "Generating your image, please wait..."              #
    #   2. Resource: {"type": "resource", "resource": {"uri": "..."}}     #
    #                                                                     #
    # We MUST NOT exit on the first text response.                        #
    # ------------------------------------------------------------------ #
    log(f"Waiting up to {wait}s for image URL (not just acknowledgement)...")
    elapsed = 0
    poll_interval = 5
    seen_log_timestamps = set()
    all_results = []       # All parsed RESULT: entries seen so far
    image_url = None
    image_metadata = {}
    terminal_error = None

    while elapsed < wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        try:
            r = requests.get(
                f"{BASE_URL}/{agent_address}/logs/latest",
                headers=headers(api_key),
                timeout=30,
            )
            if r.status_code != 200:
                continue
            logs = r.json() if isinstance(r.json(), list) else []
        except Exception:
            continue

        # Process only new log entries
        new_results_this_poll = []
        for entry in sorted(logs, key=lambda x: x.get("log_timestamp", "")):
            ts = entry.get("log_timestamp", "")
            msg = entry.get("log_entry", "")
            if ts in seen_log_timestamps:
                continue
            seen_log_timestamps.add(ts)

            if not msg.startswith("RESULT:"):
                continue

            parsed = _parse_result_entry(msg[7:])
            all_results.append(parsed)
            new_results_this_poll.append(parsed)

        # Check new entries for image URL or terminal error
        for parsed in new_results_this_poll:
            url = _extract_image_url(parsed)
            if url:
                image_url = url
                # Try to grab metadata from the resource object
                if isinstance(parsed, dict):
                    res = parsed.get("resource", {})
                    if isinstance(res, dict):
                        image_metadata = res.get("metadata", {})
                log(f"Image URL found after {elapsed}s: {image_url}")
                break

            # Check for a terminal error in text responses — no point waiting more
            if _is_text_error(parsed):
                terminal_error = str(parsed)
                log(f"Terminal error in agent response after {elapsed}s: {terminal_error[:120]}")
                break

        if image_url or terminal_error:
            break

        if all_results and not image_url:
            log(f"  ...got text response(s), still waiting for image ({elapsed}/{wait}s)")
        elif elapsed % 15 == 0:
            log(f"  ...waiting ({elapsed}/{wait}s)")

    # Stop agent
    try:
        requests.post(f"{BASE_URL}/{agent_address}/stop", headers=headers(api_key), timeout=30)
    except Exception:
        pass

    # Build output
    if image_url:
        return {
            "status": "success",
            "prompt": prompt,
            "image_url": image_url,
            "metadata": image_metadata,
            "target_agent": target,
            "relay_agent": agent_address,
            "wait_time_seconds": elapsed,
            "all_responses": all_results,
        }

    if terminal_error:
        return {
            "status": "error",
            "error": f"Image generation failed: {terminal_error}",
            "prompt": prompt,
            "target_agent": target,
            "relay_agent": agent_address,
            "all_responses": all_results,
        }

    # Timeout — but still include any text responses received (useful for debugging)
    return {
        "status": "timeout",
        "error": (
            f"No image URL received within {wait}s. "
            "Image generation may take longer — try increasing --wait. "
            f"Received {len(all_results)} text response(s) but no image URL."
        ),
        "prompt": prompt,
        "target_agent": target,
        "relay_agent": agent_address,
        "all_responses": all_results,
    }


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
        "--wait", "-w", type=int, default=90,
        help="Max seconds to wait for image generation (default: 90)",
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

    validate_agent_address(args.agent, "--agent")

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
