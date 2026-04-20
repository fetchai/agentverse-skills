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
search_agents.py — Search the Agentverse agent registry.

Searches for agents by text query, protocol digest, or tags.
Uses the V1 Search API (confirmed working).

Usage:
    python3 search_agents.py --query "image generation"
    python3 search_agents.py --query "weather" --limit 5
    python3 search_agents.py --query "DeFi" --semantic
    python3 search_agents.py --protocol proto:30a801ed...
    python3 search_agents.py --tags

Requirements:
    - requests library (pip install requests)
    - AGENTVERSE_API_KEY environment variable set

Output:
    JSON to stdout: {"status": "success", "total": N, "agents": [...]}
"""

import argparse
import json
import os
import sys

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
    print(f"[agentverse-search] {msg}", file=sys.stderr)


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


def search_agents(
    api_key: str,
    query: str,
    limit: int = 10,
    offset: int = 0,
    semantic: bool = False,
    sort: str = "relevancy",
    protocol: str | None = None,
) -> dict:
    """Search for agents in the Agentverse registry."""
    url = f"{BASE_URL}/v1/search/agents"

    payload = {
        "search_text": query,
        "semantic_search": semantic,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "direction": "desc",
        "cutoff": "balanced",
        "exclude_geo_agents": True,
        "source": "agentverse",
    }

    if protocol:
        payload["protocol_digest"] = protocol

    try:
        r = requests.post(url, headers=headers(api_key), json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()

        agents_raw = data.get("agents", [])
        total = data.get("total", len(agents_raw))

        # Normalize agent data for clean output
        agents = []
        for a in agents_raw:
            agent_info = {
                "name": a.get("name", "Unknown"),
                "address": a.get("address", ""),
                "description": a.get("short_description") or a.get("readme", "")[:200],
                "domain": a.get("domain", ""),
                "handle": a.get("handle", ""),
                "category": a.get("category", ""),
                "total_interactions": a.get("total_interactions", 0),
                "recent_interactions": a.get("recent_interactions", 0),
                "rating": a.get("rating", 0),
                "success_rate": a.get("recent_success_rate", 0),
                "protocols": a.get("protocols", []),
                "tags": a.get("system_wide_tags", []),
                "status": a.get("status", "unknown"),
            }
            agents.append(agent_info)

        return {
            "status": "success",
            "query": query,
            "semantic": semantic,
            "total": total,
            "returned": len(agents),
            "offset": offset,
            "agents": agents,
        }

    except requests.exceptions.HTTPError as e:
        return {
            "status": "error",
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"status": "error", "error": "Invalid JSON response from API"}


def get_tags(api_key: str) -> dict:
    """Get list of available agent tags."""
    url = f"{BASE_URL}/v1/search/agents/tags"

    try:
        r = requests.get(url, headers=headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()

        tags = data.get("tags", [])
        tag_names = [t.get("tag", "") for t in tags if t.get("tag")]

        return {
            "status": "success",
            "total": len(tag_names),
            "tags": sorted(tag_names),
        }

    except requests.exceptions.HTTPError as e:
        return {
            "status": "error",
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def search_by_protocol(api_key: str, protocol_digest: str, limit: int = 10) -> dict:
    """Search agents by protocol digest."""
    return search_agents(api_key, query="", limit=limit, protocol=protocol_digest)


def main():
    parser = argparse.ArgumentParser(
        description="Search the Agentverse agent registry.",
        epilog="Example: python3 search_agents.py --query 'image generation' --limit 5",
    )
    parser.add_argument(
        "--query", "-q",
        help="Search text (agent names, descriptions, capabilities)",
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=10,
        help="Max results to return (default: 10, max: 100)",
    )
    parser.add_argument(
        "--offset", type=int, default=0,
        help="Pagination offset (default: 0)",
    )
    parser.add_argument(
        "--semantic", action="store_true",
        help="Use AI-powered semantic search (slower but smarter)",
    )
    parser.add_argument(
        "--protocol",
        help="Filter by protocol digest (e.g., proto:30a801ed...)",
    )
    parser.add_argument(
        "--sort", choices=["relevancy", "created-at", "last-modified", "interactions"],
        default="relevancy",
        help="Sort order (default: relevancy)",
    )
    parser.add_argument(
        "--tags", action="store_true",
        help="List available agent tags instead of searching",
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

    if args.tags:
        result = get_tags(api_key)
    elif args.protocol and not args.query:
        result = search_by_protocol(api_key, args.protocol, args.limit)
    elif args.query:
        result = search_agents(
            api_key,
            query=args.query,
            limit=args.limit,
            offset=args.offset,
            semantic=args.semantic,
            sort=args.sort,
            protocol=args.protocol,
        )
    else:
        parser.error("Either --query, --protocol, or --tags is required")
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
