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
memory_client.py — CLI client for Agentverse Memory MCP service.

Exposes the most common memory operations as CLI commands. Outputs JSON to stdout.

Usage:
    python3 memory_client.py store-episode --agent-id AGENT --content "text"
    python3 memory_client.py query-episodes --agent-id AGENT --query "text" [--limit 10]
    python3 memory_client.py store-fact --agent-id AGENT --subject S --predicate P --object O
    python3 memory_client.py query-facts --agent-id AGENT --query "text" [--limit 10]
    python3 memory_client.py traverse-graph --agent-id AGENT --seed CONCEPT [--depth 2]
    python3 memory_client.py find-path --agent-id AGENT --start S --end E [--strategy pheromone]
    python3 memory_client.py store-procedure --agent-id AGENT --goal GOAL --steps "step1" "step2" ...
    python3 memory_client.py lookup-procedure --agent-id AGENT --goal GOAL
    python3 memory_client.py set-working --agent-id AGENT --key KEY --value VALUE [--ttl 3600]
    python3 memory_client.py get-working --agent-id AGENT --key KEY
    python3 memory_client.py health
    python3 memory_client.py stats --agent-id AGENT

Requirements:
    pip install requests

Environment:
    AM_API_KEY   — Agentverse Memory API key (am_xxxxx)
    AM_BASE_URL  — Optional: override default endpoint
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    print(
        json.dumps({"status": "error", "error": "requests not installed. Run: pip install requests"}),
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://am-server-jbneh74b5q-uc.a.run.app"
_req_id = 0


def _next_id() -> int:
    global _req_id
    _req_id += 1
    return _req_id


def get_api_key() -> str:
    key = os.environ.get("AM_API_KEY", "")
    if not key:
        print(
            json.dumps({
                "status": "error",
                "error": "AM_API_KEY environment variable not set. Get a free key:\n"
                         "  curl -X POST https://am-server-jbneh74b5q-uc.a.run.app/v1/keys \\\n"
                         "    -H 'Content-Type: application/json' \\\n"
                         "    -d '{\"agent_id\": \"my-agent\", \"tier\": \"explorer\"}'",
            }),
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def get_base_url() -> str:
    return os.environ.get("AM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


# ---------------------------------------------------------------------------
# MCP Transport
# ---------------------------------------------------------------------------

def mcp_call(tool: str, arguments: Dict[str, Any], base_url: Optional[str] = None, api_key: Optional[str] = None) -> Any:
    """Call an MCP tool via JSON-RPC 2.0 and return the parsed result."""
    url = (base_url or get_base_url()) + "/mcp"
    key = api_key or get_api_key()

    payload = {
        "jsonrpc": "2.0",
        "id": _next_id(),
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "X-API-Key": key},
            timeout=30,
        )
    except requests.exceptions.ConnectionError as e:
        return {"status": "error", "error": f"Connection failed: {e}"}
    except requests.exceptions.Timeout:
        return {"status": "error", "error": "Request timed out (30s)"}

    if resp.status_code == 401:
        return {"status": "error", "error": "Unauthorized — check AM_API_KEY"}
    if resp.status_code == 429:
        reset = resp.headers.get("X-RateLimit-Reset", "unknown")
        return {"status": "error", "error": f"Rate limit exceeded. Reset at: {reset}"}
    if resp.status_code >= 400:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        return {"status": "error", "error": f"HTTP {resp.status_code}: {err}"}

    try:
        rpc = resp.json()
    except Exception:
        return {"status": "error", "error": f"Invalid JSON response: {resp.text[:200]}"}

    if "error" in rpc:
        # Top-level JSON-RPC error (e.g. unknown method, auth gate).
        return {"status": "error", "error": rpc["error"]}

    result_obj = rpc.get("result", {})

    # MCP-spec migration (#81): tool-execution errors are now reported
    # IN-BAND as result.isError == true with a structured error payload,
    # NOT as a top-level JSON-RPC error. Surface them as a CLI error.
    if isinstance(result_obj, dict) and result_obj.get("isError"):
        sc = result_obj.get("structuredContent") or {}
        err = sc.get("error")
        if err is None:
            try:
                err = result_obj["content"][0]["text"]
            except (KeyError, IndexError, TypeError):
                err = "tool execution error"
        return {"status": "error", "error": err}

    # Prefer the typed structuredContent payload (MCP-spec result shape).
    if isinstance(result_obj, dict) and "structuredContent" in result_obj:
        return result_obj["structuredContent"]

    # Fallback: extract inner JSON from the text content envelope.
    try:
        text = result_obj["content"][0]["text"]
        return json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return result_obj if result_obj else rpc


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_store_episode(args: argparse.Namespace) -> Dict[str, Any]:
    arguments: Dict[str, Any] = {"agent_id": args.agent_id, "content": args.content}
    if args.session_id:
        arguments["session_id"] = args.session_id
    if args.source:
        arguments["source"] = args.source
    return mcp_call("memory_store_episode", arguments)


def cmd_query_episodes(args: argparse.Namespace) -> Any:
    arguments: Dict[str, Any] = {"agent_id": args.agent_id, "query": args.query, "limit": args.limit}
    if args.session_id:
        arguments["session_id"] = args.session_id
    if args.use_hybrid is not None:
        arguments["use_hybrid"] = args.use_hybrid
    if args.use_pheromone:
        arguments["use_pheromone"] = True
    result = mcp_call("memory_search_episodes", arguments)
    return result


def cmd_list_episodes(args: argparse.Namespace) -> Any:
    arguments: Dict[str, Any] = {"agent_id": args.agent_id, "limit": args.limit, "offset": args.offset}
    return mcp_call("memory_get_episodes", arguments)


def cmd_store_fact(args: argparse.Namespace) -> Dict[str, Any]:
    arguments: Dict[str, Any] = {
        "agent_id": args.agent_id,
        "subject": args.subject,
        "predicate": args.predicate,
        "object": args.object,
    }
    if args.confidence is not None:
        arguments["confidence"] = args.confidence
    if args.source:
        arguments["source"] = args.source
    return mcp_call("memory_graph_add_triple", arguments)


def cmd_query_facts(args: argparse.Namespace) -> Any:
    arguments: Dict[str, Any] = {"agent_id": args.agent_id, "query": args.query, "limit": args.limit}
    return mcp_call("memory_query_graph", arguments)


def cmd_traverse_graph(args: argparse.Namespace) -> Any:
    arguments: Dict[str, Any] = {
        "agent_id": args.agent_id,
        "start_id": args.seed,
        "max_depth": args.depth,
        "limit": args.limit,
    }
    return mcp_call("memory_traverse_graph", arguments)


def cmd_find_path(args: argparse.Namespace) -> Any:
    arguments: Dict[str, Any] = {
        "agent_id": args.agent_id,
        "start_concept": args.start,
        "end_concept": args.end,
        "strategy": args.strategy,
        "max_hops": args.max_hops,
    }
    return mcp_call("memory_find_path", arguments)


def cmd_store_procedure(args: argparse.Namespace) -> Dict[str, Any]:
    arguments: Dict[str, Any] = {
        "agent_id": args.agent_id,
        "name": args.goal,
        "steps": args.steps,
    }
    return mcp_call("memory_store_procedure", arguments)


def cmd_lookup_procedure(args: argparse.Namespace) -> Any:
    arguments: Dict[str, Any] = {
        "agent_id": args.agent_id,
        "task": args.goal,
    }
    if args.min_success_rate is not None:
        arguments["min_success_rate"] = args.min_success_rate
    return mcp_call("memory_match_procedure", arguments)


def cmd_set_working(args: argparse.Namespace) -> Dict[str, Any]:
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value  # treat as plain string
    arguments: Dict[str, Any] = {"agent_id": args.agent_id, "key": args.key, "value": value}
    if args.ttl is not None:
        arguments["ttl_seconds"] = args.ttl
    return mcp_call("memory_set_working", arguments)


def cmd_get_working(args: argparse.Namespace) -> Any:
    return mcp_call("memory_get_working", {"agent_id": args.agent_id, "key": args.key})


def cmd_clear_working(args: argparse.Namespace) -> Any:
    arguments: Dict[str, Any] = {"agent_id": args.agent_id}
    if args.key:
        arguments["key"] = args.key
    elif args.prefix:
        arguments["prefix"] = args.prefix
    return mcp_call("memory_clear_working", arguments)


def cmd_health(_args: argparse.Namespace) -> Any:
    # Health uses GET /health endpoint directly for speed
    base_url = get_base_url()
    try:
        resp = requests.get(base_url + "/health", timeout=10)
        return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


def cmd_stats(args: argparse.Namespace) -> Any:
    return mcp_call("memory_get_stats", {"agent_id": args.agent_id})


def cmd_create_key(args: argparse.Namespace) -> Any:
    base_url = get_base_url()
    try:
        resp = requests.post(
            base_url + "/v1/keys",
            json={"agent_id": args.agent_id, "tier": args.tier},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="memory_client.py",
        description="Agentverse Memory CLI — 35 MCP tools for AI agent memory",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # store-episode
    ep = sub.add_parser("store-episode", help="Store an episodic memory")
    ep.add_argument("--agent-id", required=True)
    ep.add_argument("--content", required=True)
    ep.add_argument("--session-id")
    ep.add_argument("--source", choices=["user", "agent", "tool", "external"], default="agent")

    # query-episodes
    qe = sub.add_parser("query-episodes", help="Search episodic memories (hybrid TF-IDF + dense)")
    qe.add_argument("--agent-id", required=True)
    qe.add_argument("--query", required=True)
    qe.add_argument("--limit", type=int, default=10)
    qe.add_argument("--session-id")
    # Default retrieval is hybrid (TF-IDF lexical ∪ dense embeddings, fused via RRF).
    # Pass --no-hybrid to force lexical-only TF-IDF; --use-pheromone to re-rank by
    # pheromone weight (best for warm/repeated-access workloads; off by default).
    qe.add_argument("--use-hybrid", dest="use_hybrid", action="store_true", default=None)
    qe.add_argument("--no-hybrid", dest="use_hybrid", action="store_false")
    qe.add_argument("--use-pheromone", dest="use_pheromone", action="store_true", default=False)

    # list-episodes
    le = sub.add_parser("list-episodes", help="List recent episodic memories")
    le.add_argument("--agent-id", required=True)
    le.add_argument("--limit", type=int, default=20)
    le.add_argument("--offset", type=int, default=0)

    # store-fact
    sf = sub.add_parser("store-fact", help="Store a knowledge graph triple")
    sf.add_argument("--agent-id", required=True)
    sf.add_argument("--subject", required=True)
    sf.add_argument("--predicate", required=True)
    sf.add_argument("--object", required=True)
    sf.add_argument("--confidence", type=float)
    sf.add_argument("--source")

    # query-facts
    qf = sub.add_parser("query-facts", help="Search the knowledge graph")
    qf.add_argument("--agent-id", required=True)
    qf.add_argument("--query", required=True)
    qf.add_argument("--limit", type=int, default=10)

    # traverse-graph
    tg = sub.add_parser("traverse-graph", help="Traverse the graph from a seed concept")
    tg.add_argument("--agent-id", required=True)
    tg.add_argument("--seed", required=True, metavar="CONCEPT")
    tg.add_argument("--depth", type=int, default=2)
    tg.add_argument("--limit", type=int, default=20)

    # find-path
    fp = sub.add_parser("find-path", help="Find path between two concepts (A*)")
    fp.add_argument("--agent-id", required=True)
    fp.add_argument("--start", required=True)
    fp.add_argument("--end", required=True)
    fp.add_argument("--strategy", choices=["pheromone", "shortest", "semantic"], default="pheromone")
    fp.add_argument("--max-hops", type=int, default=5)

    # store-procedure
    sp = sub.add_parser("store-procedure", help="Store a procedural memory (goal + steps)")
    sp.add_argument("--agent-id", required=True)
    sp.add_argument("--goal", required=True)
    sp.add_argument("--steps", nargs="+", required=True, metavar="STEP")

    # lookup-procedure
    lp = sub.add_parser("lookup-procedure", help="Find best procedure for a goal")
    lp.add_argument("--agent-id", required=True)
    lp.add_argument("--goal", required=True)
    lp.add_argument("--min-success-rate", type=float)

    # set-working
    sw = sub.add_parser("set-working", help="Set working memory key")
    sw.add_argument("--agent-id", required=True)
    sw.add_argument("--key", required=True)
    sw.add_argument("--value", required=True, help="JSON value or plain string")
    sw.add_argument("--ttl", type=int, metavar="SECONDS")

    # get-working
    gw = sub.add_parser("get-working", help="Get working memory value")
    gw.add_argument("--agent-id", required=True)
    gw.add_argument("--key", required=True)

    # clear-working
    cw = sub.add_parser("clear-working", help="Clear working memory")
    cw.add_argument("--agent-id", required=True)
    cw.add_argument("--key")
    cw.add_argument("--prefix")

    # health
    sub.add_parser("health", help="Check service health")

    # stats
    st = sub.add_parser("stats", help="Get agent memory stats")
    st.add_argument("--agent-id", required=True)

    # create-key
    ck = sub.add_parser("create-key", help="Get a free API key")
    ck.add_argument("--agent-id", required=True)
    ck.add_argument("--tier", choices=["explorer", "builder", "pro"], default="explorer")

    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "store-episode": cmd_store_episode,
    "query-episodes": cmd_query_episodes,
    "list-episodes": cmd_list_episodes,
    "store-fact": cmd_store_fact,
    "query-facts": cmd_query_facts,
    "traverse-graph": cmd_traverse_graph,
    "find-path": cmd_find_path,
    "store-procedure": cmd_store_procedure,
    "lookup-procedure": cmd_lookup_procedure,
    "set-working": cmd_set_working,
    "get-working": cmd_get_working,
    "clear-working": cmd_clear_working,
    "health": cmd_health,
    "stats": cmd_stats,
    "create-key": cmd_create_key,
}


def main() -> None:
    parser = build_parser()
    # Fix argparse attribute names (replace hyphens)
    args = parser.parse_args()
    # Normalize attribute names
    for attr in list(vars(args).keys()):
        if "-" in attr:
            setattr(args, attr.replace("-", "_"), getattr(args, attr))

    handler = COMMAND_MAP.get(args.command)
    if not handler:
        print(json.dumps({"status": "error", "error": f"Unknown command: {args.command}"}))
        sys.exit(1)

    result = handler(args)
    print(json.dumps(result, indent=2))

    # Exit 1 on error
    if isinstance(result, dict) and result.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
