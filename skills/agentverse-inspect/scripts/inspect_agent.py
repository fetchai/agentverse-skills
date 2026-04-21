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
inspect_agent.py — Inspect an Agentverse agent's details, protocols, and status.

Queries both the Almanac (public on-chain registry) and the Search API to get
comprehensive information about any registered agent.

Usage:
    python3 inspect_agent.py --agent agent1q...
    python3 inspect_agent.py --agent agent1q... --full
    python3 inspect_agent.py --recent  # Show recently registered agents

Requirements:
    - requests library (pip install requests)
    - AGENTVERSE_API_KEY environment variable (optional for almanac reads, required for search)

Output:
    JSON to stdout: {"status": "success", "agent": {...}}
"""

import argparse
import json
import os
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print(
        json.dumps({"status": "error", "error": "requests library not installed. Run: pip install requests"}),
        file=sys.stdout,
    )
    sys.exit(1)


BASE_URL = "https://agentverse.ai"


def log(msg: str) -> None:
    """Print log message to stderr."""
    print(f"[agentverse-inspect] {msg}", file=sys.stderr)


def get_api_key() -> Optional[str]:
    """Get Agentverse API key from environment (optional for public endpoints)."""
    return os.environ.get("AGENTVERSE_API_KEY", "").strip() or None


def headers(api_key: Optional[str]) -> dict:
    """Standard headers."""
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def get_almanac_info(agent_address: str, api_key: Optional[str]) -> Optional[dict]:
    """Get agent info from the V1 Almanac (public, no auth needed)."""
    url = f"{BASE_URL}/v1/almanac/agents/{agent_address}"
    try:
        r = requests.get(url, headers=headers(api_key), timeout=30)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            log(f"Agent not found in Almanac: {agent_address}")
            return None
        else:
            log(f"Almanac query returned {r.status_code}")
            return None
    except Exception as e:
        log(f"Almanac query error: {e}")
        return None


def get_search_info(agent_address: str, api_key: Optional[str]) -> Optional[dict]:
    """Search for agent in the registry to get rich metadata."""
    if not api_key:
        return None

    url = f"{BASE_URL}/v1/search/agents"
    payload = {
        "search_text": agent_address,
        "semantic_search": False,
        "limit": 5,
        "offset": 0,
        "sort": "relevancy",
        "direction": "desc",
        "cutoff": "none",
        "source": "agentverse",
    }

    try:
        r = requests.post(url, headers=headers(api_key), json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            agents = data.get("agents", [])
            # Find exact match
            for a in agents:
                if a.get("address") == agent_address:
                    return a
            # Return first result if address was partial
            if agents:
                return agents[0]
        return None
    except Exception as e:
        log(f"Search query error: {e}")
        return None


def get_hosting_info(agent_address: str, api_key: Optional[str]) -> Optional[dict]:
    """Get hosting profile (public endpoint)."""
    if not api_key:
        return None

    url = f"{BASE_URL}/v1/hosting/agents/{agent_address}/profile"
    try:
        r = requests.get(url, headers=headers(api_key), timeout=30)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def get_recent_agents(api_key: Optional[str], limit: int = 20) -> dict:
    """Get recently registered agents from the Almanac."""
    url = f"{BASE_URL}/v1/almanac/recent"
    try:
        r = requests.get(url, headers=headers(api_key), timeout=30)
        if r.status_code == 200:
            agents_raw = r.json()
            if isinstance(agents_raw, list):
                agents = []
                for a in agents_raw[:limit]:
                    agents.append({
                        "address": a.get("address", ""),
                        "domain": a.get("domain_name", ""),
                        "status": a.get("status", ""),
                        "type": a.get("type", ""),
                        "endpoints": a.get("endpoints", []),
                        "protocols": [p.get("digest", "") for p in a.get("protocols", [])],
                        "expiry": a.get("expiry", ""),
                    })
                return {
                    "status": "success",
                    "total": len(agents),
                    "agents": agents,
                }
            return {"status": "success", "total": 0, "agents": []}
        else:
            return {"status": "error", "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def inspect_agent(agent_address: str, api_key: Optional[str], full: bool = False) -> dict:
    """Gather all available information about an agent."""
    log(f"Inspecting agent: {agent_address}")

    # Gather from multiple sources
    almanac = get_almanac_info(agent_address, api_key)
    search = get_search_info(agent_address, api_key)
    hosting = get_hosting_info(agent_address, api_key)

    if not almanac and not search and not hosting:
        return {
            "status": "not_found",
            "error": f"Agent not found in Almanac, Search, or Hosting: {agent_address}",
            "suggestions": [
                "Check the address is correct (should start with 'agent1q')",
                "The agent may not be registered in the Almanac yet",
                "Try searching by name instead: search_agents.py --query 'agent name'",
            ],
        }

    # Build combined info
    agent_info = {
        "address": agent_address,
        "found_in": [],
    }

    # Almanac data (on-chain registration)
    if almanac:
        agent_info["found_in"].append("almanac")
        agent_info["almanac"] = {
            "status": almanac.get("status", "unknown"),
            "type": almanac.get("type", ""),
            "domain": almanac.get("domain_name", ""),
            "endpoints": almanac.get("endpoints", []),
            "protocols": almanac.get("protocols", []),
            "expiry": almanac.get("expiry", ""),
            "metadata": almanac.get("metadata", {}),
        }

        # Extract protocol digests for easy reference
        protocols = almanac.get("protocols", [])
        if protocols:
            agent_info["protocol_digests"] = [
                p.get("digest", "") for p in protocols if isinstance(p, dict)
            ]

    # Search data (marketplace metadata)
    if search:
        agent_info["found_in"].append("search")
        agent_info["marketplace"] = {
            "name": search.get("name", ""),
            "handle": search.get("handle", ""),
            "domain": search.get("domain", ""),
            "category": search.get("category", ""),
            "description": search.get("short_description") or search.get("readme", "")[:300],
            "tags": search.get("system_wide_tags", []),
            "total_interactions": search.get("total_interactions", 0),
            "recent_interactions": search.get("recent_interactions", 0),
            "rating": search.get("rating", 0),
            "success_rate": search.get("recent_success_rate", 0),
            "owner": search.get("owner", ""),
            "status": search.get("status", ""),
        }

        if full:
            agent_info["marketplace"]["protocols"] = search.get("protocols", [])
            agent_info["marketplace"]["readme"] = search.get("readme", "")

    # Hosting data (if hosted on Agentverse)
    if hosting:
        agent_info["found_in"].append("hosting")
        agent_info["hosting"] = {
            "name": hosting.get("name", ""),
            "author": hosting.get("author_username", ""),
            "domain": hosting.get("domain", ""),
            "running": hosting.get("running", False),
            "description": hosting.get("short_description", ""),
            "readme": hosting.get("readme", "")[:300] if not full else hosting.get("readme", ""),
            "avatar_url": hosting.get("avatar_url", ""),
            "metadata": hosting.get("metadata", {}),
        }

    # Summary
    agent_info["summary"] = {
        "name": (
            (search or {}).get("name")
            or (hosting or {}).get("name")
            or (almanac or {}).get("domain_name")
            or "Unknown"
        ),
        "online": (
            (almanac or {}).get("status") == "active"
            or (hosting or {}).get("running", False)
        ),
        "is_hosted": hosting is not None,
        "has_almanac": almanac is not None,
        "in_marketplace": search is not None,
    }

    return {
        "status": "success",
        "agent": agent_info,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Inspect an Agentverse agent — view protocols, endpoints, metadata, and status.",
        epilog="Example: python3 inspect_agent.py --agent agent1q...",
    )
    parser.add_argument(
        "--agent", "-a",
        help="Agent address to inspect (agent1q...)",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Include full readme and protocol details",
    )
    parser.add_argument(
        "--recent", action="store_true",
        help="Show recently registered agents instead of inspecting one",
    )
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Number of recent agents to show (default: 20)",
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

    if args.recent:
        result = get_recent_agents(api_key, limit=args.limit)
    elif args.agent:
        result = inspect_agent(args.agent, api_key, full=args.full)
    else:
        parser.error("Either --agent or --recent is required")
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
