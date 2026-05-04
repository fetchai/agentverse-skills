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
agentverse_relay.py -- Shared relay agent management for agentverse-skills.

Provides common utilities for finding, creating, managing, and cleaning up
relay agents used by agentverse-chat and agentverse-image-gen skills.

This module resolves several architectural issues:
- Race condition: each invocation can use a unique relay via session IDs (#14)
- Agent hijacking: no fallback to arbitrary stopped agents (#15)
- Code duplication: single source of truth for relay logic (#23)
- Relay cleanup: auto-cleanup and manual cleanup support (#24)
"""

import ast
import json
import os
import re
import sys
import time
from typing import Callable, List, Optional, Tuple

try:
    import requests
except ImportError:
    print(
        json.dumps({
            "status": "error",
            "error": "requests library not installed. Run: pip install requests",
        }),
        file=sys.stdout,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://agentverse.ai/v1/hosting/agents"

# Relay agents are identified by this prefix. Session-specific relays append
# a suffix: "agentverse-skills-relay-a1b2c3d4".
RELAY_AGENT_PREFIX = "agentverse-skills-relay"

# Pre-processing regex: strip UUID(...) calls so ast.literal_eval can parse
# Python reprs that include uuid.UUID objects (e.g. from uagents
# ResourceContent).
_UUID_RE = re.compile(r"\bUUID\('([0-9a-f-]+)'\)")


# ---------------------------------------------------------------------------
# Logger -- replaced by consuming scripts via set_logger()
# ---------------------------------------------------------------------------

_log_fn: Callable[[str], None] = lambda msg: None


def set_logger(fn: Callable[[str], None]) -> None:
    """Set the log function used by relay operations."""
    global _log_fn
    _log_fn = fn


def _log(msg: str) -> None:
    _log_fn(msg)


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def get_api_key() -> str:
    """Get Agentverse API key from environment."""
    key = os.environ.get("AGENTVERSE_API_KEY", "").strip()
    if not key:
        print(
            json.dumps({
                "status": "error",
                "error": (
                    "AGENTVERSE_API_KEY environment variable not set. "
                    "Get your key at https://agentverse.ai/profile/api-keys"
                ),
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


# ---------------------------------------------------------------------------
# Agent lifecycle operations
# ---------------------------------------------------------------------------

def list_agents(api_key: str) -> list:
    """List all hosted agents."""
    try:
        r = requests.get(BASE_URL, headers=headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("items", data) if isinstance(data, dict) else data
    except Exception as e:
        _log(f"Warning: error listing agents: {e}")
        return []


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
        _log(f"Code upload failed: {r.status_code} {r.text[:200]}")
        return False
    except Exception as e:
        _log(f"Code upload error: {e}")
        return False


def stop_agent(api_key: str, agent_address: str) -> None:
    """Stop a hosted agent (fire-and-forget)."""
    try:
        requests.post(
            f"{BASE_URL}/{agent_address}/stop",
            headers=headers(api_key),
            timeout=30,
        )
    except Exception:
        pass


def start_agent(api_key: str, agent_address: str) -> bool:
    """Start a hosted agent. Returns True on success."""
    try:
        r = requests.post(
            f"{BASE_URL}/{agent_address}/start",
            headers=headers(api_key),
            timeout=30,
        )
        return r.status_code in (200, 201)
    except Exception as e:
        _log(f"Start error: {e}")
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
        _log(f"Logs error: {e}")
    return []


def delete_agent(api_key: str, agent_address: str) -> bool:
    """Delete a hosted agent. Returns True on success."""
    try:
        r = requests.delete(
            f"{BASE_URL}/{agent_address}",
            headers=headers(api_key),
            timeout=30,
        )
        return r.status_code in (200, 204)
    except Exception as e:
        _log(f"Delete error: {e}")
        return False


# ---------------------------------------------------------------------------
# Relay agent management
# ---------------------------------------------------------------------------

def _is_relay_agent(name: str) -> bool:
    """Check if an agent name matches the relay naming convention."""
    return name is not None and name.startswith(RELAY_AGENT_PREFIX)


def find_relay_agent(api_key: str, name: Optional[str] = None) -> Optional[str]:
    """Find an existing relay agent by name.

    Only returns agents that match the relay naming convention
    (``agentverse-skills-relay*``). Never falls back to arbitrary agents.

    Args:
        api_key: Agentverse API key.
        name: Specific relay name to search for. If None, returns the first
            relay agent found matching the prefix.

    Returns:
        Agent address string, or None if not found.
    """
    agents = list_agents(api_key)
    for agent in agents:
        agent_name = agent.get("name", "")
        if name:
            if agent_name == name:
                return agent.get("address")
        else:
            if _is_relay_agent(agent_name):
                return agent.get("address")
    return None


def create_relay_agent(api_key: str, name: Optional[str] = None) -> Optional[str]:
    """Create a new relay agent.

    Args:
        api_key: Agentverse API key.
        name: Agent name. Defaults to ``RELAY_AGENT_PREFIX``.

    Returns:
        Agent address string, or None on failure.
    """
    relay_name = name or RELAY_AGENT_PREFIX
    try:
        r = requests.post(
            BASE_URL,
            headers=headers(api_key),
            json={"name": relay_name},
            timeout=30,
        )
        if r.status_code in (200, 201):
            address = r.json().get("address")
            _log(f"Created relay agent: {address} (name: {relay_name})")
            return address
        else:
            detail = r.text[:200]
            _log(f"Warning: could not create relay agent: {r.status_code} {detail}")
    except Exception as e:
        _log(f"Warning: error creating relay agent: {e}")
    return None


def find_or_create_relay(
    api_key: str,
    session_id: Optional[str] = None,
) -> str:
    """Find an existing relay agent or create one.

    If ``session_id`` is provided, uses a unique relay name to avoid
    conflicts between concurrent invocations. Otherwise uses the shared
    default name.

    Never falls back to hijacking arbitrary stopped agents (see issue #15).
    If no relay can be found or created, prints an error and exits.

    Args:
        api_key: Agentverse API key.
        session_id: Optional session identifier for concurrent isolation.
            When set, the relay will be named
            ``agentverse-skills-relay-{session_id}``.

    Returns:
        Agent address string.

    Raises:
        SystemExit: If no relay agent can be found or created.
    """
    if session_id:
        relay_name = f"{RELAY_AGENT_PREFIX}-{session_id}"
    else:
        relay_name = RELAY_AGENT_PREFIX

    # Try to find an existing relay with this exact name
    address = find_relay_agent(api_key, name=relay_name)
    if address:
        _log(f"Using existing relay agent: {address} (name: {relay_name})")
        return address

    # If no session_id, also accept any relay matching the prefix
    if not session_id:
        address = find_relay_agent(api_key)
        if address:
            _log(f"Using existing relay agent: {address}")
            return address

    # Create a new relay
    address = create_relay_agent(api_key, name=relay_name)
    if address:
        return address

    # Cannot find or create -- fail with a clear error instead of hijacking
    print(
        json.dumps({
            "status": "error",
            "error": (
                "Could not find or create a relay agent. "
                "You may have reached the hosted agent limit. "
                "Run `python3 manage_agents.py cleanup` to remove old relays, "
                "or specify --relay with an existing agent address."
            ),
        }),
        file=sys.stdout,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Relay cleanup
# ---------------------------------------------------------------------------

def cleanup_relay_agents(api_key: str, keep_count: int = 0) -> List[str]:
    """Delete relay agents matching the naming convention.

    Args:
        api_key: Agentverse API key.
        keep_count: Number of relay agents to keep (0 = delete all).
            When > 0, keeps the most recently updated ones.

    Returns:
        List of deleted agent addresses.
    """
    agents = list_agents(api_key)
    relays = []
    for agent in agents:
        name = agent.get("name", "")
        if _is_relay_agent(name):
            relays.append(agent)

    if not relays:
        _log("No relay agents found to clean up.")
        return []

    # Sort by update timestamp (newest first) so we keep the most recent
    relays.sort(
        key=lambda a: a.get("code_update_timestamp", ""),
        reverse=True,
    )

    to_delete = relays[keep_count:]
    deleted = []

    for agent in to_delete:
        addr = agent.get("address", "")
        name = agent.get("name", "")
        if delete_agent(api_key, addr):
            _log(f"Cleaned up relay agent: {name} ({addr[:30]}...)")
            deleted.append(addr)
        else:
            _log(f"Warning: failed to delete relay {name} ({addr[:30]}...)")

    return deleted


# ---------------------------------------------------------------------------
# Result parsing (unified -- handles both chat and image-gen responses)
# ---------------------------------------------------------------------------

def parse_result_entry(result_str: str):
    """Parse a RESULT: log entry string into a Python object.

    Uses a multi-stage strategy:
    1. Direct ``json.loads`` (handles valid JSON)
    2. ``ast.literal_eval`` after stripping ``UUID(...)`` calls (handles
       Python repr with apostrophes and uagents UUID fields)
    3. Falls back to raw string -- never silently drops content
    """
    # Stage 1: direct JSON
    try:
        return json.loads(result_str)
    except (json.JSONDecodeError, ValueError):
        pass

    # Stage 2: ast.literal_eval with UUID cleanup
    cleaned = _UUID_RE.sub(r"'\1'", result_str)
    try:
        return ast.literal_eval(cleaned)
    except (ValueError, SyntaxError):
        pass

    # Stage 3: raw string fallback
    return result_str


def extract_results(logs: list) -> list:
    """Extract and parse all RESULT: entries from agent logs.

    Sorts by timestamp, extracts entries prefixed with ``RESULT:``,
    and parses each using ``parse_result_entry``.
    """
    results = []
    sorted_logs = sorted(logs, key=lambda x: x.get("log_timestamp", ""))
    for entry in sorted_logs:
        msg = entry.get("log_entry", "")
        if msg.startswith("RESULT:"):
            results.append(parse_result_entry(msg[7:]))
    return results


def extract_status(logs: list, prefix: str = "CHAT_STATUS:") -> str:
    """Extract the latest status value from logs.

    Args:
        logs: Log entries from the agent.
        prefix: Status prefix to look for (e.g. "CHAT_STATUS:" or
            "IMAGE_STATUS:").

    Returns:
        Latest status string, or "unknown".
    """
    status = "unknown"
    sorted_logs = sorted(logs, key=lambda x: x.get("log_timestamp", ""))
    for entry in sorted_logs:
        msg = entry.get("log_entry", "")
        if msg.startswith(prefix):
            status = msg[len(prefix):]
    return status


# ---------------------------------------------------------------------------
# Public URL resolution (agent-storage:// → HTTPS)
# ---------------------------------------------------------------------------

def resolve_public_url(uri: str) -> Optional[str]:
    """Convert an ``agent-storage://`` URI to a direct HTTPS URL.

    Agentverse image agents return images as ``agent-storage://`` URIs::

        agent-storage://https://agentverse.ai/v1/storage/<uuid>

    The ``agent-storage://`` prefix is a protocol hint for the Agentverse
    web UI; the remainder is a valid HTTPS URL that can be opened directly
    in a browser or downloaded with ``requests.get(url)``.

    Args:
        uri: The URI string to resolve.

    Returns:
        A direct HTTPS URL string, or ``None`` if the URI cannot be
        resolved to a public HTTP(S) URL.
    """
    if not uri:
        return None
    if uri.startswith("agent-storage://"):
        # Strip the scheme prefix — the remainder is always a valid HTTPS URL
        return uri[len("agent-storage://"):]
    if uri.startswith("http://") or uri.startswith("https://"):
        return uri
    return None


def enrich_with_public_url(results: list) -> list:
    """Post-process a results list to add ``public_url`` to resource entries.

    For each result that is a ResourceContent dict (``type == "resource"``),
    resolves the ``uri`` field to a direct HTTPS URL and adds it as
    ``public_url`` at the top level of the entry.  This lets callers open
    or display images without needing to understand the ``agent-storage://``
    scheme.

    Example input entry::

        {"type": "resource", "resource": {
            "uri": "agent-storage://https://agentverse.ai/v1/storage/abc-123",
            "metadata": {"mime_type": "image/png", "role": "generated-image"}
        }}

    Example output entry::

        {"type": "resource", "resource": {...},
         "public_url": "https://agentverse.ai/v1/storage/abc-123"}

    Args:
        results: List of parsed RESULT entries (from ``extract_results``).

    Returns:
        New list with ``public_url`` fields added where applicable.
        Non-resource entries and entries with non-resolvable URIs are passed
        through unchanged.
    """
    enriched = []
    for item in results:
        if isinstance(item, dict) and item.get("type") == "resource":
            resource = item.get("resource", {})
            if isinstance(resource, dict):
                uri = resource.get("uri", "")
                public_url = resolve_public_url(uri)
                if public_url:
                    item = dict(item)  # shallow copy — don't mutate original
                    item["public_url"] = public_url
        enriched.append(item)
    return enriched
