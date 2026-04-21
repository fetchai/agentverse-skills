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
manage_agents.py — Manage hosted Agentverse agents.

List, start, stop, view logs, and delete hosted agents.

Usage:
    python3 manage_agents.py list
    python3 manage_agents.py start --agent agent1q...
    python3 manage_agents.py stop --agent agent1q...
    python3 manage_agents.py logs --agent agent1q...
    python3 manage_agents.py delete --agent agent1q...
    python3 manage_agents.py code --agent agent1q...
    python3 manage_agents.py info --agent agent1q...

Requirements:
    - requests library (pip install requests)
    - AGENTVERSE_API_KEY environment variable set

Output:
    JSON to stdout
"""

import argparse
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    print(
        json.dumps({"status": "error", "error": "requests library not installed. Run: pip install requests"}),
        file=sys.stdout,
    )
    sys.exit(1)


BASE_URL = "https://agentverse.ai/v1/hosting/agents"


def log(msg: str) -> None:
    """Print log message to stderr."""
    print(f"[agentverse-manage] {msg}", file=sys.stderr)


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


def cmd_list(api_key: str, running_only: bool = False) -> dict:
    """List all hosted agents."""
    try:
        r = requests.get(BASE_URL, headers=headers(api_key), timeout=30)
        r.raise_for_status()
        data = r.json()
        agents_raw = data.get("items", data) if isinstance(data, dict) else data

        agents = []
        for a in agents_raw:
            agent_info = {
                "name": a.get("name", "Unknown"),
                "address": a.get("address", ""),
                "running": a.get("running", False),
                "compiled": a.get("compiled", False),
                "domain": a.get("domain", ""),
                "wallet_address": a.get("wallet_address", ""),
                "created": a.get("creation_timestamp", ""),
                "updated": a.get("code_update_timestamp", ""),
            }
            if running_only and not agent_info["running"]:
                continue
            agents.append(agent_info)

        return {
            "status": "success",
            "total": len(agents),
            "agents": agents,
        }

    except requests.exceptions.HTTPError as e:
        return {"status": "error", "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def cmd_start(api_key: str, agent_address: str) -> dict:
    """Start a hosted agent."""
    try:
        r = requests.post(
            f"{BASE_URL}/{agent_address}/start",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code in (200, 201):
            data = r.json()
            return {
                "status": "success",
                "action": "start",
                "agent": agent_address,
                "running": data.get("running", True),
                "name": data.get("name", ""),
            }
        else:
            return {"status": "error", "error": f"Start failed: HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def cmd_stop(api_key: str, agent_address: str) -> dict:
    """Stop a hosted agent."""
    try:
        r = requests.post(
            f"{BASE_URL}/{agent_address}/stop",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code in (200, 201):
            data = r.json()
            return {
                "status": "success",
                "action": "stop",
                "agent": agent_address,
                "running": data.get("running", False),
                "name": data.get("name", ""),
            }
        else:
            return {"status": "error", "error": f"Stop failed: HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def cmd_logs(api_key: str, agent_address: str, tail: int = 50) -> dict:
    """Get latest logs from a hosted agent."""
    try:
        r = requests.get(
            f"{BASE_URL}/{agent_address}/logs/latest",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code == 200:
            logs_raw = r.json() if isinstance(r.json(), list) else []
            # Sort by timestamp
            sorted_logs = sorted(logs_raw, key=lambda x: x.get("log_timestamp", ""))
            # Take last N entries
            recent = sorted_logs[-tail:]

            entries = []
            for entry in recent:
                entries.append({
                    "timestamp": entry.get("log_timestamp", ""),
                    "message": entry.get("log_entry", ""),
                    "level": entry.get("log_level", "info"),
                })

            return {
                "status": "success",
                "agent": agent_address,
                "total_entries": len(logs_raw),
                "showing": len(entries),
                "logs": entries,
            }
        elif r.status_code == 405:
            return {
                "status": "error",
                "error": "Logs endpoint returned 405 (Method Not Allowed). "
                         "This is a known Agentverse API issue. "
                         "Try starting the agent first — logs may only be available while running.",
            }
        else:
            return {"status": "error", "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def cmd_delete(api_key: str, agent_address: str) -> dict:
    """Delete a hosted agent."""
    try:
        # Stop first if running
        requests.post(f"{BASE_URL}/{agent_address}/stop", headers=headers(api_key), timeout=30)
    except Exception:
        pass

    try:
        r = requests.delete(
            f"{BASE_URL}/{agent_address}",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code in (200, 201, 204):
            return {
                "status": "success",
                "action": "delete",
                "agent": agent_address,
                "message": "Agent deleted successfully",
            }
        elif r.status_code == 404:
            return {"status": "error", "error": f"Agent not found: {agent_address}"}
        else:
            return {"status": "error", "error": f"Delete failed: HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def cmd_code(api_key: str, agent_address: str) -> dict:
    """Get the source code of a hosted agent."""
    try:
        r = requests.get(
            f"{BASE_URL}/{agent_address}/code",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            code_files = data.get("code", [])
            # code_files is a list of {language, name, value}
            files = []
            if isinstance(code_files, str):
                try:
                    code_files = json.loads(code_files)
                except json.JSONDecodeError:
                    code_files = [{"language": "python", "name": "agent.py", "value": code_files}]

            for f in code_files:
                files.append({
                    "name": f.get("name", "unknown"),
                    "language": f.get("language", "python"),
                    "content": f.get("value", ""),
                    "lines": len(f.get("value", "").split("\n")),
                })

            return {
                "status": "success",
                "agent": agent_address,
                "digest": data.get("digest", ""),
                "timestamp": data.get("timestamp", ""),
                "files": files,
            }
        elif r.status_code == 404:
            return {"status": "error", "error": f"Agent not found or no code uploaded: {agent_address}"}
        else:
            return {"status": "error", "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def cmd_restart(api_key: str, agent_address: str, delay: int = 3) -> dict:
    """Restart a hosted agent (stop → wait → start).

    If the agent is already stopped, the stop step is skipped gracefully
    and the start proceeds immediately.
    """
    log(f"Restarting agent: {agent_address}")

    # Stop (tolerate if already stopped)
    try:
        r = requests.post(
            f"{BASE_URL}/{agent_address}/stop",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code in (200, 201):
            log("Agent stopped")
        else:
            # If stop fails with non-fatal code, just continue to start
            log(f"Stop returned {r.status_code} (proceeding with start)")
    except requests.exceptions.RequestException as e:
        log(f"Stop request failed (proceeding with start): {e}")

    # Brief pause so the platform can settle before restart
    time.sleep(delay)

    # Start
    try:
        r = requests.post(
            f"{BASE_URL}/{agent_address}/start",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code in (200, 201):
            data = r.json()
            return {
                "status": "success",
                "action": "restart",
                "agent": agent_address,
                "running": data.get("running", True),
                "name": data.get("name", ""),
            }
        else:
            return {
                "status": "error",
                "error": f"Restart: start failed with HTTP {r.status_code}: {r.text[:200]}",
            }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Restart: start request failed: {str(e)}"}


def cmd_info(api_key: str, agent_address: str) -> dict:
    """Get detailed info about a hosted agent."""
    try:
        r = requests.get(
            f"{BASE_URL}/{agent_address}",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "status": "success",
                "agent": {
                    "name": data.get("name", ""),
                    "address": data.get("address", ""),
                    "running": data.get("running", False),
                    "compiled": data.get("compiled", False),
                    "domain": data.get("domain", ""),
                    "prefix": data.get("prefix", ""),
                    "wallet_address": data.get("wallet_address", ""),
                    "code_digest": data.get("code_digest", ""),
                    "revision": data.get("revision", 0),
                    "readme": data.get("readme", ""),
                    "short_description": data.get("short_description", ""),
                    "metadata": data.get("metadata", {}),
                    "avatar_url": data.get("avatar_url", ""),
                    "created": data.get("creation_timestamp", ""),
                    "updated": data.get("code_update_timestamp", ""),
                },
            }
        elif r.status_code == 404:
            return {"status": "error", "error": f"Agent not found: {agent_address}"}
        else:
            return {"status": "error", "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def main():
    parser = argparse.ArgumentParser(
        description="Manage hosted Agentverse agents.",
        epilog=(
            "Commands:\n"
            "  list     List all hosted agents\n"
            "  start    Start a hosted agent\n"
            "  stop     Stop a hosted agent\n"
            "  restart  Restart a hosted agent (stop then start)\n"
            "  logs     Get latest logs from an agent\n"
            "  delete   Delete a hosted agent\n"
            "  code     View agent source code\n"
            "  info     Get detailed agent info\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["list", "start", "stop", "restart", "logs", "delete", "code", "info"],
        help="Action to perform",
    )
    parser.add_argument(
        "--agent", "-a",
        help="Agent address (required for start/stop/restart/logs/delete/code/info)",
    )
    parser.add_argument(
        "--running", action="store_true",
        help="Only show running agents (for 'list' command)",
    )
    parser.add_argument(
        "--tail", "-t", type=int, default=50,
        help="Number of log entries to show (for 'logs' command, default: 50)",
    )
    parser.add_argument(
        "--delay", type=int, default=3,
        help="Seconds to wait between stop and start for 'restart' command (default: 3)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging to stderr",
    )

    args = parser.parse_args()

    if not args.verbose:
        global log
        log = lambda msg: None  # noqa: E731

    # Validate that --agent is provided for commands that need it
    if args.command in ("start", "stop", "restart", "logs", "delete", "code", "info") and not args.agent:
        parser.error(f"--agent is required for '{args.command}' command")
        sys.exit(1)

    api_key = get_api_key()

    # Dispatch command
    if args.command == "list":
        result = cmd_list(api_key, running_only=args.running)
    elif args.command == "start":
        result = cmd_start(api_key, args.agent)
    elif args.command == "stop":
        result = cmd_stop(api_key, args.agent)
    elif args.command == "restart":
        result = cmd_restart(api_key, args.agent, delay=args.delay)
    elif args.command == "logs":
        result = cmd_logs(api_key, args.agent, tail=args.tail)
    elif args.command == "delete":
        result = cmd_delete(api_key, args.agent)
    elif args.command == "code":
        result = cmd_code(api_key, args.agent)
    elif args.command == "info":
        result = cmd_info(api_key, args.agent)
    else:
        result = {"status": "error", "error": f"Unknown command: {args.command}"}

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
