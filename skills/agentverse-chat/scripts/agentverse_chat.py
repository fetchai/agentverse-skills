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
agentverse_chat.py — Send a message to any Agentverse agent and get the response.

Self-bootstrapping: finds or creates a relay agent automatically.
Uses the Agentverse Hosted Agent pattern (no public IP needed).

Usage:
    python3 agentverse_chat.py --target agent1q... --message "Hello"
    python3 agentverse_chat.py --target agent1q... --message "Hello" --wait 60
    python3 agentverse_chat.py --target agent1q... --message "Hello" --relay agent1q...

Requirements:
    - requests library (pip install requests)
    - AGENTVERSE_API_KEY environment variable set

Output:
    JSON to stdout: {"status": "success", "responses": [...]}
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
RELAY_AGENT_NAME = "agentverse-skills-relay"


def log(msg: str) -> None:
    """Print log message to stderr (keeps stdout clean for JSON output)."""
    print(f"[agentverse-chat] {msg}", file=sys.stderr)


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
    """Standard headers for Agentverse API."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def find_relay_agent(api_key: str) -> Optional[str]:
    """Find an existing relay agent by name."""
    try:
        r = requests.get(BASE_URL, headers=headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()
        agents = data.get("items", data) if isinstance(data, dict) else data
        for agent in agents:
            if agent.get("name") == RELAY_AGENT_NAME:
                return agent.get("address")
    except Exception as e:
        log(f"Warning: error listing agents: {e}")
    return None


def create_relay_agent(api_key: str) -> Optional[str]:
    """Create a new relay agent for chat relay."""
    try:
        r = requests.post(
            BASE_URL,
            headers=headers(api_key),
            json={"name": RELAY_AGENT_NAME},
            timeout=30,
        )
        if r.status_code in (200, 201):
            data = r.json()
            address = data.get("address")
            log(f"Created relay agent: {address}")
            return address
        else:
            log(f"Warning: could not create relay agent: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log(f"Warning: error creating relay agent: {e}")
    return None


def find_or_create_relay(api_key: str) -> str:
    """Find an existing relay agent or create one."""
    address = find_relay_agent(api_key)
    if address:
        log(f"Using existing relay agent: {address}")
        return address

    address = create_relay_agent(api_key)
    if address:
        return address

    # Fallback: try to use any stopped agent
    try:
        r = requests.get(BASE_URL, headers=headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()
        agents = data.get("items", data) if isinstance(data, dict) else data
        for agent in agents:
            if not agent.get("running"):
                addr = agent.get("address")
                log(f"Fallback: using existing stopped agent: {addr}")
                return addr
    except Exception:
        pass

    print(
        json.dumps({
            "status": "error",
            "error": "Could not find or create a relay agent. "
                     "Specify --relay with an existing agent address, or delete unused agents."
        }),
        file=sys.stdout,
    )
    sys.exit(1)


def build_chat_code(target_address: str, message: str, start_session: bool = False) -> str:
    """Build the hosted agent code that sends a chat message and captures response.

    Args:
        target_address: The agent address to send the message to.
        message: The text message to send.
        start_session: If True, send a StartSessionContent message first before the
            ChatMessage. Some agents (particularly stateful or multi-turn agents)
            require this handshake before they will respond to messages.
    """
    # Escape the message for embedding in Python source
    escaped_message = message.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    # Build the startup handler body depending on whether session init is needed
    if start_session:
        startup_body = f'''    ctx.logger.info("CHAT_STATUS:sending_session_start")
    await ctx.send(TARGET, ChatMessage(
        timestamp=datetime.now(),
        msg_id=uuid4(),
        content=[StartSessionContent(type="start-session")],
    ))
    ctx.logger.info("CHAT_STATUS:session_start_sent")
    # Small delay to let the target process the session start before the main message
    await asyncio.sleep(2)
    ctx.logger.info("CHAT_STATUS:sending")
    await ctx.send(TARGET, ChatMessage(
        timestamp=datetime.now(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=MESSAGE)],
    ))
    ctx.logger.info("CHAT_STATUS:sent")'''
        extra_imports = "import asyncio\n"
        start_session_import = "StartSessionContent, "
    else:
        startup_body = f'''    ctx.logger.info("CHAT_STATUS:sending")
    await ctx.send(TARGET, ChatMessage(
        timestamp=datetime.now(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=MESSAGE)],
    ))
    ctx.logger.info("CHAT_STATUS:sent")'''
        extra_imports = ""
        start_session_import = ""

    return f'''{extra_imports}from datetime import datetime
from uuid import uuid4
from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage, ChatAcknowledgement, {start_session_import}TextContent, chat_protocol_spec
)

TARGET = "{target_address}"
MESSAGE = "{escaped_message}"

protocol = Protocol(spec=chat_protocol_spec)

@agent.on_event("startup")
async def send_msg(ctx: Context):
{startup_body}

@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info("CHAT_STATUS:ack_received")

@protocol.on_message(ChatMessage)
async def handle_response(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info("CHAT_STATUS:response_received")
    for item in msg.content:
        try:
            item_dict = item.dict() if hasattr(item, "dict") else str(item)
            ctx.logger.info("RESULT:" + str(item_dict))
        except Exception as e:
            ctx.logger.info("RESULT:" + repr(item))

agent.include(protocol, publish_manifest=True)
'''


def upload_code(api_key: str, agent_address: str, code: str) -> bool:
    """Upload code to a hosted agent."""
    files = [{"language": "python", "name": "agent.py", "value": code}]
    payload = {"code": json.dumps(files)}
    try:
        r = requests.put(
            f"{BASE_URL}/{agent_address}/code",
            headers=headers(api_key),
            json=payload,
            timeout=30,
        )
        if r.status_code in (200, 201, 204):
            return True
        log(f"Code upload failed: {r.status_code} {r.text[:200]}")
        return False
    except Exception as e:
        log(f"Code upload error: {e}")
        return False


def stop_agent(api_key: str, agent_address: str) -> None:
    """Stop a hosted agent."""
    try:
        requests.post(
            f"{BASE_URL}/{agent_address}/stop",
            headers=headers(api_key),
            timeout=30,
        )
    except Exception:
        pass


def start_agent(api_key: str, agent_address: str) -> bool:
    """Start a hosted agent."""
    try:
        r = requests.post(
            f"{BASE_URL}/{agent_address}/start",
            headers=headers(api_key),
            timeout=30,
        )
        return r.status_code in (200, 201)
    except Exception as e:
        log(f"Start error: {e}")
        return False


def get_logs(api_key: str, agent_address: str) -> list:
    """Get latest logs from a hosted agent."""
    try:
        r = requests.get(
            f"{BASE_URL}/{agent_address}/logs/latest",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code == 200:
            return r.json() if isinstance(r.json(), list) else []
    except Exception as e:
        log(f"Logs error: {e}")
    return []


def extract_results(logs: list) -> list:
    """Extract RESULT: entries from agent logs.

    Parses each RESULT: entry using a multi-stage strategy that handles:
    - Valid JSON (direct json.loads)
    - Python repr format (ast.literal_eval — correctly handles apostrophes)
    - Raw strings as fallback (never silently drops content)
    """
    import ast

    results = []
    # Sort by timestamp to get chronological order
    sorted_logs = sorted(logs, key=lambda x: x.get("log_timestamp", ""))
    for entry in sorted_logs:
        msg = entry.get("log_entry", "")
        if msg.startswith("RESULT:"):
            result_str = msg[7:]
            parsed = None

            # Stage 1: try direct JSON parsing (handles proper JSON)
            try:
                parsed = json.loads(result_str)
            except (json.JSONDecodeError, ValueError):
                pass

            # Stage 2: try ast.literal_eval (handles Python repr with apostrophes,
            # single-quoted strings, None/True/False)
            if parsed is None:
                try:
                    parsed = ast.literal_eval(result_str)
                except (ValueError, SyntaxError):
                    pass

            # Stage 3: fall back to raw string — never silently drop content
            results.append(parsed if parsed is not None else result_str)

    return results


def extract_status(logs: list) -> str:
    """Extract the latest CHAT_STATUS from logs."""
    status = "unknown"
    sorted_logs = sorted(logs, key=lambda x: x.get("log_timestamp", ""))
    for entry in sorted_logs:
        msg = entry.get("log_entry", "")
        if msg.startswith("CHAT_STATUS:"):
            status = msg[12:]
    return status


def run_chat(
    target: str,
    message: str,
    wait: int,
    relay: Optional[str],
    start_session: bool = False,
) -> dict:
    """Execute the full chat workflow.

    Args:
        target: Target agent address.
        message: Text message to send.
        wait: Max seconds to wait for a response.
        relay: Optional relay agent address (auto-detected if None).
        start_session: If True, send StartSessionContent before the ChatMessage.
            Use this for agents that require explicit session initiation.
            See agentverse-chat/SKILL.md for guidance on which agents need this.
    """
    api_key = get_api_key()

    # Step 1: Find or create relay agent
    if relay:
        agent_address = relay
        log(f"Using specified relay agent: {agent_address}")
    else:
        agent_address = find_or_create_relay(api_key)

    # Step 2: Stop any running instance
    log("Stopping relay agent (if running)...")
    stop_agent(api_key, agent_address)
    time.sleep(2)

    # Step 3: Build and upload code
    log(f"Building chat code for target: {target}" + (" (with session start)" if start_session else ""))
    code = build_chat_code(target, message, start_session=start_session)

    log("Uploading code...")
    if not upload_code(api_key, agent_address, code):
        return {"status": "error", "error": "Failed to upload code to relay agent"}

    time.sleep(1)

    # Step 4: Start agent
    log("Starting relay agent...")
    if not start_agent(api_key, agent_address):
        return {"status": "error", "error": "Failed to start relay agent"}

    # Step 5: Wait for response
    log(f"Waiting {wait}s for response...")
    elapsed = 0
    poll_interval = 5
    results = []

    while elapsed < wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        # Check logs for results
        logs = get_logs(api_key, agent_address)
        results = extract_results(logs)
        status = extract_status(logs)

        if results:
            log(f"Got {len(results)} response(s) after {elapsed}s")
            break

        if elapsed % 15 == 0:
            log(f"  ...waiting ({elapsed}/{wait}s, status: {status})")

    # Step 6: Stop agent
    log("Stopping relay agent...")
    stop_agent(api_key, agent_address)

    # Step 7: Return results
    if results:
        return {
            "status": "success",
            "responses": results,
            "relay_agent": agent_address,
            "target": target,
            "wait_time_seconds": elapsed,
        }
    else:
        # Get final logs for debugging
        final_logs = get_logs(api_key, agent_address)
        log_entries = [e.get("log_entry", "") for e in sorted(final_logs, key=lambda x: x.get("log_timestamp", ""))]
        return {
            "status": "timeout",
            "error": f"No response received within {wait}s",
            "relay_agent": agent_address,
            "target": target,
            "last_status": extract_status(final_logs),
            "log_entries": log_entries[-10:],  # Last 10 log entries for debugging
        }


def main():
    parser = argparse.ArgumentParser(
        description="Send a message to an Agentverse agent and get the response.",
        epilog="Example: python3 agentverse_chat.py --target agent1q... --message 'Hello!'",
    )
    parser.add_argument(
        "--target", required=True,
        help="Target agent address (agent1q...)",
    )
    parser.add_argument(
        "--message", required=True,
        help="Message to send to the target agent",
    )
    parser.add_argument(
        "--wait", type=int, default=45,
        help="Max seconds to wait for response (default: 45)",
    )
    parser.add_argument(
        "--relay",
        help="Specific relay agent address to use (optional, auto-detected if omitted)",
    )
    parser.add_argument(
        "--start-session", action="store_true", dest="start_session",
        help=(
            "Send a StartSessionContent message before the main ChatMessage. "
            "Required by some stateful or multi-turn agents that expect an explicit "
            "session handshake before responding. Most agents do NOT need this — "
            "only use if you're getting no response from an agent that normally works."
        ),
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging to stderr",
    )

    args = parser.parse_args()

    if not args.verbose:
        # Suppress log messages unless verbose
        global log
        log = lambda msg: None  # noqa: E731

    result = run_chat(
        target=args.target,
        message=args.message,
        wait=args.wait,
        relay=args.relay,
        start_session=args.start_session,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
