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
deploy_agent.py — Deploy a Python agent to Agentverse hosting.

Creates a new hosted agent, uploads code, and optionally starts it.
Supports both file-based and inline code deployment.

Usage:
    python3 deploy_agent.py --name "my-agent" --file agent_code.py
    python3 deploy_agent.py --name "my-agent" --code 'print("hello")'
    python3 deploy_agent.py --name "my-agent" --file agent.py --start
    python3 deploy_agent.py --name "my-agent" --file agent.py --file requirements.txt

Requirements:
    - requests library (pip install requests)
    - AGENTVERSE_API_KEY environment variable set

Output:
    JSON to stdout: {"status": "success", "address": "agent1q...", "running": false}
"""

import argparse
import json
import os
import sys
import time
from typing import Tuple

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
    print(f"[agentverse-deploy] {msg}", file=sys.stderr)


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


def create_agent(api_key: str, name: str) -> dict:
    """Create a new hosted agent."""
    try:
        r = requests.post(
            BASE_URL,
            headers=headers(api_key),
            json={"name": name},
            timeout=30,
        )
        if r.status_code in (200, 201):
            return {"success": True, "data": r.json()}
        elif r.status_code == 400:
            error_text = r.text
            if "limit" in error_text.lower() or "maximum" in error_text.lower():
                # Don't hardcode the limit — report what the API says and let the user act on it.
                # Use `manage_agents.py list` to see current agents and delete unused ones.
                return {
                    "success": False,
                    "error": (
                        f"Agent limit reached: {error_text[:200]}. "
                        "Delete unused agents with `manage_agents.py delete --agent <address>`."
                    ),
                }
            return {"success": False, "error": f"Bad request: {error_text[:200]}"}
        elif r.status_code == 409:
            return {"success": False, "error": f"Agent with name '{name}' already exists."}
        else:
            return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}


def upload_code(api_key: str, agent_address: str, files: list) -> dict:
    """Upload code files to a hosted agent.
    
    Args:
        files: List of dicts with keys: language, name, value
    """
    payload = {"code": json.dumps(files)}
    try:
        r = requests.put(
            f"{BASE_URL}/{agent_address}/code",
            headers=headers(api_key),
            json=payload,
            timeout=30,
        )
        if r.status_code in (200, 201, 204):
            return {"success": True}
        else:
            return {"success": False, "error": f"Code upload failed: HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Upload request failed: {str(e)}"}


def start_agent(api_key: str, agent_address: str) -> dict:
    """Start a hosted agent."""
    try:
        r = requests.post(
            f"{BASE_URL}/{agent_address}/start",
            headers=headers(api_key),
            timeout=30,
        )
        if r.status_code in (200, 201):
            return {"success": True, "data": r.json()}
        else:
            return {"success": False, "error": f"Start failed: HTTP {r.status_code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Start request failed: {str(e)}"}


def detect_language(filename: str) -> str:
    """Detect file language from extension."""
    ext = os.path.splitext(filename)[1].lower()
    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".json": "json",
        ".txt": "text",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
    }
    return language_map.get(ext, "python")


def read_file(filepath: str) -> Tuple[str, str]:
    """Read a file and return (filename, content)."""
    if not os.path.exists(filepath):
        print(
            json.dumps({"status": "error", "error": f"File not found: {filepath}"}),
            file=sys.stdout,
        )
        sys.exit(1)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        filename = os.path.basename(filepath)
        return filename, content
    except Exception as e:
        print(
            json.dumps({"status": "error", "error": f"Error reading file {filepath}: {e}"}),
            file=sys.stdout,
        )
        sys.exit(1)


def deploy(name: str, code_files: list, start: bool, api_key: str) -> dict:
    """Full deployment workflow: create agent, upload code, optionally start."""
    # Step 1: Create agent
    log(f"Creating agent '{name}'...")
    result = create_agent(api_key, name)
    if not result["success"]:
        return {"status": "error", "error": result["error"]}

    agent_data = result["data"]
    agent_address = agent_data.get("address", "")
    log(f"Created agent: {agent_address}")

    # Step 2: Upload code
    log(f"Uploading {len(code_files)} file(s)...")
    time.sleep(1)  # Brief pause to let agent initialize

    upload_result = upload_code(api_key, agent_address, code_files)
    if not upload_result["success"]:
        return {
            "status": "error",
            "error": upload_result["error"],
            "address": agent_address,
            "note": "Agent was created but code upload failed. Use manage_agents.py to retry or delete.",
        }

    log("Code uploaded successfully")

    # Step 3: Optionally start
    running = False
    if start:
        log("Starting agent...")
        time.sleep(1)
        start_result = start_agent(api_key, agent_address)
        if start_result["success"]:
            running = True
            log("Agent started successfully")
        else:
            log(f"Warning: Agent created and code uploaded, but start failed: {start_result['error']}")
            return {
                "status": "partial",
                "address": agent_address,
                "name": name,
                "running": False,
                "warning": f"Start failed: {start_result['error']}",
                "note": "Agent created and code uploaded. Start manually with manage_agents.py.",
            }

    return {
        "status": "success",
        "address": agent_address,
        "name": name,
        "running": running,
        "files_uploaded": len(code_files),
        "file_names": [f["name"] for f in code_files],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Deploy a Python agent to Agentverse hosting.",
        epilog=(
            "Examples:\n"
            "  python3 deploy_agent.py --name my-agent --file agent.py\n"
            "  python3 deploy_agent.py --name my-agent --code '@agent.on_event(\"startup\")\\nasync def start(ctx): pass'\n"
            "  python3 deploy_agent.py --name my-agent --file agent.py --start\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--name", "-n", required=True,
        help="Name for the new agent",
    )
    parser.add_argument(
        "--file", "-f", action="append", default=[],
        help="Python file(s) to upload (can specify multiple). First file should be agent.py",
    )
    parser.add_argument(
        "--code", "-c",
        help="Inline Python code to deploy (alternative to --file)",
    )
    parser.add_argument(
        "--start", "-s", action="store_true",
        help="Start the agent immediately after deployment",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging to stderr",
    )

    args = parser.parse_args()

    if not args.verbose:
        global log
        log = lambda msg: None  # noqa: E731

    if not args.file and not args.code:
        parser.error("Either --file or --code is required")
        sys.exit(1)

    api_key = get_api_key()

    # Build code files list
    code_files = []

    if args.code:
        # Inline code → agent.py
        code_files.append({
            "language": "python",
            "name": "agent.py",
            "value": args.code,
        })
    else:
        # File-based deployment
        for filepath in args.file:
            filename, content = read_file(filepath)
            language = detect_language(filename)
            code_files.append({
                "language": language,
                "name": filename,
                "value": content,
            })

        # Ensure agent.py is the first/primary file
        agent_py_files = [f for f in code_files if f["name"] == "agent.py"]
        if not agent_py_files and len(code_files) == 1:
            # If single file uploaded, rename to agent.py
            code_files[0]["name"] = "agent.py"

    result = deploy(
        name=args.name,
        code_files=code_files,
        start=args.start,
        api_key=api_key,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
