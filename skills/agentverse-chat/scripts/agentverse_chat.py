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
    python3 agentverse_chat.py --target agent1q... --message "Hello" --cleanup

Requirements:
    - requests library (pip install requests)
    - AGENTVERSE_API_KEY environment variable set

Output:
    JSON to stdout: {"status": "success", "responses": [...]}
"""

import argparse
import json
import os
import re
import sys
import time
from typing import Optional
from uuid import uuid4

# ---------------------------------------------------------------------------
# Import shared relay utilities
# ---------------------------------------------------------------------------
_COMMON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_common")
sys.path.insert(0, _COMMON_DIR)
from agentverse_relay import (  # noqa: E402
    BASE_URL,
    delete_agent,
    enrich_with_public_url,
    extract_acks,
    extract_results,
    extract_status,
    find_or_create_relay,
    get_api_key,
    get_logs,
    headers,
    is_answer_content,
    is_terminal_content,
    latest_log_timestamp,
    set_logger,
    start_agent,
    stop_agent,
    upload_code,
)

_AGENT_ADDR_RE = re.compile(r"^agent1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{59}$")


def validate_agent_address(address: str, flag_name: str = "--target") -> None:
    """Validate agent address format (bech32, 65 chars)."""
    if not _AGENT_ADDR_RE.match(address):
        print(json.dumps({
            "status": "error",
            "error": f"Invalid agent address format: {address!r}",
            "hint": "Expected format: agent1q... (65 characters). Use agentverse-search to find addresses.",
        }))
        sys.exit(1)


def log(msg: str) -> None:
    """Print log message to stderr (keeps stdout clean for JSON output)."""
    print(f"[agentverse-chat] {msg}", file=sys.stderr)


def build_chat_code(
    target_address: str,
    message: str,
    start_session: bool = False,
    run_id: Optional[str] = None,
    msg_id: Optional[str] = None,
) -> str:
    """Build the hosted agent code that sends a chat message and captures response.

    Args:
        target_address: The agent address to send the message to.
        message: The text message to send.
        start_session: If True, send a StartSessionContent message first before the
            ChatMessage. Some agents (particularly stateful or multi-turn agents)
            require this handshake before they will respond to messages.
        run_id: Correlation id for this invocation. Every line the relay logs is
            tagged with it so results can be told apart from ones left in the
            log buffer by earlier runs. Generated if omitted.
        msg_id: The outgoing ChatMessage's msg_id. Generated here rather than in
            the relay so the caller knows it up front and can match it against
            the acknowledged_msg_id the target sends back. Generated if omitted.
    """
    # Escape the message for embedding in Python source
    escaped_message = message.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    run_id = run_id or uuid4().hex[:8]
    msg_id = msg_id or str(uuid4())

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
        msg_id=UUID(MSG_ID),
        content=[TextContent(type="text", text=MESSAGE)],
    ))
    ctx.logger.info("CHAT_STATUS:sent")'''
        extra_imports = "import asyncio\n"
        start_session_import = "StartSessionContent, "
    else:
        startup_body = f'''    ctx.logger.info("CHAT_STATUS:sending")
    await ctx.send(TARGET, ChatMessage(
        timestamp=datetime.now(),
        msg_id=UUID(MSG_ID),
        content=[TextContent(type="text", text=MESSAGE)],
    ))
    ctx.logger.info("CHAT_STATUS:sent")'''
        extra_imports = ""
        start_session_import = ""

    return f'''{extra_imports}from datetime import datetime
from uuid import UUID, uuid4
from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage, ChatAcknowledgement, {start_session_import}TextContent, chat_protocol_spec
)

TARGET = "{target_address}"
MESSAGE = "{escaped_message}"
RUN_ID = "{run_id}"
MSG_ID = "{msg_id}"

protocol = Protocol(spec=chat_protocol_spec)

@agent.on_event("startup")
async def send_msg(ctx: Context):
{startup_body}

@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info("CHAT_ACK:" + RUN_ID + ":" + sender + ":" + str(msg.acknowledged_msg_id))
    ctx.logger.info("CHAT_STATUS:ack_received")

@protocol.on_message(ChatMessage)
async def handle_response(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info("CHAT_STATUS:response_received")
    for item in msg.content:
        try:
            item_dict = item.dict() if hasattr(item, "dict") else str(item)
            ctx.logger.info("RESULT:" + RUN_ID + ":" + sender + ":" + str(item_dict))
        except Exception as e:
            ctx.logger.info("RESULT:" + RUN_ID + ":" + sender + ":" + repr(item))

agent.include(protocol, publish_manifest=True)
'''


def run_chat(
    target: str,
    message: str,
    wait: int,
    relay: Optional[str],
    start_session: bool = False,
    cleanup: bool = False,
    settle: int = 0,
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
        cleanup: If True, delete the relay agent after use (when auto-created).
    """
    api_key = get_api_key()

    # Correlation id for this invocation: names the session relay, tags every
    # line the relay logs, and filters the results we are willing to accept.
    run_id = uuid4().hex[:8]
    msg_id = str(uuid4())

    # Step 1: Find or create relay agent
    auto_created = False
    session_relay = False
    if relay:
        agent_address = relay
        log(f"Using specified relay agent: {agent_address}")
    else:
        # Session relay: the name carries this invocation's id, so concurrent
        # runs cannot stop, overwrite or read each other's relay (issue #14)
        agent_address = find_or_create_relay(api_key, session_id=run_id)
        auto_created = True
        session_relay = True

    try:
        # Step 2: Stop any running instance
        log("Stopping relay agent (if running)...")
        stop_agent(api_key, agent_address)
        time.sleep(2)

        # Hosted agent logs survive the stop/upload/start cycle, so note how far
        # the buffer already reaches — anything at or before this is not ours.
        since = latest_log_timestamp(get_logs(api_key, agent_address)) or None

        # Step 3: Build and upload code
        log(f"Building chat code for target: {target}" + (" (with session start)" if start_session else ""))
        code = build_chat_code(
            target, message, start_session=start_session, run_id=run_id, msg_id=msg_id
        )

        log("Uploading code...")
        if not upload_code(api_key, agent_address, code):
            return {"status": "error", "error": "Failed to upload code to relay agent"}

        time.sleep(1)

        # Step 4: Start agent
        log("Starting relay agent...")
        if not start_agent(api_key, agent_address):
            return {"status": "error", "error": "Failed to start relay agent"}

        # Step 5: Wait for response
        # The Chat Protocol places no upper bound on how many ChatMessages a
        # target may send in reply to one inbound message, and nothing marks
        # which of them is the answer. Stopping at the first RESULT: therefore
        # returns a progress line, or a session welcome, as though it were the
        # response (#42). Exit conditions, in order of confidence:
        #
        #   1. A terminal content item (end-session / end-stream). The target
        #      has said it is finished. Unambiguous, and free.
        #   2. An answer has arrived and `settle` seconds have passed with no
        #      new content. With settle=0 -- the default -- this is exactly the
        #      previous behaviour, so nobody pays latency they did not ask for.
        #   3. `wait` expires.
        #
        # Bookkeeping items never satisfy (2) on their own: session and stream
        # markers and attachment metadata are protocol control flow, not the
        # reply the caller asked for. That part costs nothing and is on by
        # default; collecting *later* messages is what costs time, so it is
        # opt-in via --settle.
        log(f"Waiting {wait}s for response...")
        elapsed = 0
        poll_interval = 5
        results = []
        logs = []
        answered = False
        last_result_count = 0
        quiet_since = 0

        while elapsed < wait:
            time.sleep(poll_interval)
            elapsed += poll_interval

            # Check logs for results — only ones this run's relay attributed to
            # the agent we actually asked
            logs = get_logs(api_key, agent_address)
            results = extract_results(
                logs, since=since, run_id=run_id, expected_sender=target
            )
            status = extract_status(logs, since=since)

            if len(results) > last_result_count:
                last_result_count = len(results)
                # New content arrived: restart the quiet period.
                quiet_since = elapsed
                if not answered:
                    answered = any(is_answer_content(r) for r in results)

            if any(is_terminal_content(r) for r in results):
                log(f"Target signalled end of exchange after {elapsed}s "
                    f"({len(results)} response(s))")
                break

            if answered and (elapsed - quiet_since) >= settle:
                log(f"Got {len(results)} response(s) after {elapsed}s")
                break

            if elapsed % 15 == 0:
                waiting_for = "follow-ups" if answered else "response"
                log(f"  ...waiting for {waiting_for} ({elapsed}/{wait}s, status: {status})")

        # Step 6: Stop agent
        log("Stopping relay agent...")
        stop_agent(api_key, agent_address)

        # Step 7: Return results.
        # Bookkeeping-only content is not an answer, so a run that collected
        # nothing but session markers is a timeout, not a success (#42).
        if results and answered:
            # Enrich resource responses with direct browser-openable public_url
            # (converts agent-storage:// URIs to HTTPS URLs)
            results = enrich_with_public_url(results)
            return {
                "status": "success",
                "responses": results,
                "relay_agent": agent_address,
                "target": target,
                "run_id": run_id,
                # Reported only — a target may reply without ever acking, so
                # this never decides whether the run succeeded.
                "acknowledged": msg_id in extract_acks(
                    logs, since=since, run_id=run_id, expected_sender=target
                ),
                "wait_time_seconds": elapsed,
            }
        else:
            # Get final logs for debugging — this run's only, so a reused relay
            # does not pad the dump with an earlier run's lines
            final_logs = get_logs(api_key, agent_address)
            sorted_final = sorted(final_logs, key=lambda x: x.get("log_timestamp", ""))
            log_entries = [
                e.get("log_entry", "") for e in sorted_final
                if since is None or e.get("log_timestamp", "") > since
            ]
            return {
                "status": "timeout",
                "error": f"No response received within {wait}s",
                "relay_agent": agent_address,
                "target": target,
                "run_id": run_id,
                "msg_id": msg_id,
                # Distinguishes "the target never received it" from "it received
                # the message and sent no reply".
                "acknowledged": msg_id in extract_acks(
                    final_logs, since=since, run_id=run_id, expected_sender=target
                ),
                "last_status": extract_status(final_logs, since=since),
                "log_entries": log_entries[-10:],  # Last 10 log entries for debugging
            }
    finally:
        # Cleanup: delete the relay agent if --cleanup was requested and we
        # auto-managed it. A session relay's name carries this invocation's id,
        # so nothing can ever reuse it — always delete those, or they pile up
        # against the hosted agent limit.
        if auto_created and (cleanup or session_relay):
            log("Cleaning up relay agent...")
            if delete_agent(api_key, agent_address):
                log(f"Relay agent deleted: {agent_address}")
            else:
                log(f"Warning: failed to delete relay agent: {agent_address}")


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
        "--cleanup", action="store_true",
        help="Delete the relay agent after use (auto-created relays are per-invocation and always deleted)",
    )
    parser.add_argument(
        "--settle", type=int, default=0, metavar="SECONDS",
        help=(
            "After the first answer arrives, keep collecting for this many "
            "seconds of quiet before returning. The Chat Protocol lets an "
            "agent send several messages per reply with no general "
            "end-of-turn marker, so agents that emit a progress line before "
            "the answer need this. Default 0 = return on the first answer "
            "(previous behaviour). end-session / end-stream still returns "
            "immediately, so streaming agents never pay the wait."
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

    # Wire the shared module's logger to our log function
    set_logger(log)

    validate_agent_address(args.target, "--target")

    result = run_chat(
        target=args.target,
        message=args.message,
        wait=args.wait,
        relay=args.relay,
        start_session=args.start_session,
        cleanup=args.cleanup,
        settle=args.settle,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
