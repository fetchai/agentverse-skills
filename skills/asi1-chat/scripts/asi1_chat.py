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
asi1_chat.py — Chat with ASI:One (Fetch.ai's agentic LLM).

OpenAI-compatible API for the ASI Alliance's language model.
Supports both standard and streaming responses.

Usage:
    python3 asi1_chat.py --prompt "What is Fetch.ai?"
    python3 asi1_chat.py --prompt "Explain AI agents" --model asi1-mini
    python3 asi1_chat.py --prompt "Write code" --system "You are a Python expert"
    python3 asi1_chat.py --prompt "Hello" --stream
    python3 asi1_chat.py --prompt "Complex question" --max-tokens 2000

Requirements:
    - requests library (pip install requests)
    - ASI_ONE_API_KEY environment variable set

Output:
    JSON to stdout: {"status": "success", "response": "...", "usage": {...}}
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


API_URL = "https://api.asi1.ai/v1/chat/completions"
DEFAULT_MODEL = "asi1-mini"


def log(msg: str) -> None:
    """Print log message to stderr."""
    print(f"[asi1-chat] {msg}", file=sys.stderr)


def get_api_key() -> str:
    """Get ASI:One API key from environment."""
    key = os.environ.get("ASI_ONE_API_KEY", "").strip()
    if not key:
        print(
            json.dumps({
                "status": "error",
                "error": "ASI_ONE_API_KEY environment variable not set. "
                         "Get your key at https://asi1.ai (ASI Alliance)"
            }),
            file=sys.stdout,
        )
        sys.exit(1)
    return key


def chat_completion(
    api_key: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    stream: bool = False,
) -> dict:
    """Send a chat completion request to ASI:One API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Build messages
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }

    try:
        if stream:
            return _stream_response(headers, payload)
        else:
            return _standard_response(headers, payload)
    except requests.exceptions.Timeout:
        return {"status": "error", "error": "Request timed out. Try a shorter prompt or increase timeout."}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "error": "Connection failed. Check your internet connection and that api.asi1.ai is reachable."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Request failed: {str(e)}"}


def _standard_response(headers: dict, payload: dict) -> dict:
    """Handle standard (non-streaming) response."""
    r = requests.post(API_URL, headers=headers, json=payload, timeout=120)

    if r.status_code == 200:
        data = r.json()
        choices = data.get("choices", [])
        if not choices:
            return {"status": "error", "error": "No choices in response"}

        message = choices[0].get("message", {})
        content = message.get("content", "")
        finish_reason = choices[0].get("finish_reason", "")

        usage = data.get("usage", {})

        return {
            "status": "success",
            "model": data.get("model", payload.get("model", "")),
            "response": content,
            "finish_reason": finish_reason,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        }
    elif r.status_code == 401:
        return {"status": "error", "error": "Authentication failed. Check your ASI_ONE_API_KEY."}
    elif r.status_code == 429:
        return {"status": "error", "error": "Rate limited. Wait a moment and try again."}
    elif r.status_code == 400:
        try:
            error_data = r.json()
            error_msg = error_data.get("error", {}).get("message", r.text[:200])
        except Exception:
            error_msg = r.text[:200]
        return {"status": "error", "error": f"Bad request: {error_msg}"}
    else:
        return {"status": "error", "error": f"HTTP {r.status_code}: {r.text[:200]}"}


def _stream_response(headers: dict, payload: dict) -> dict:
    """Handle streaming response (SSE)."""
    full_content = ""
    model_name = payload.get("model", "")
    finish_reason = ""

    r = requests.post(API_URL, headers=headers, json=payload, timeout=120, stream=True)

    if r.status_code != 200:
        if r.status_code == 401:
            return {"status": "error", "error": "Authentication failed. Check your ASI_ONE_API_KEY."}
        return {"status": "error", "error": f"HTTP {r.status_code}: {r.text[:200]}"}

    try:
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    if chunk.get("model"):
                        model_name = chunk["model"]
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_content += content
                            # Print chunks to stderr for real-time feedback
                            print(content, end="", file=sys.stderr, flush=True)
                        fr = choices[0].get("finish_reason")
                        if fr:
                            finish_reason = fr
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        if full_content:
            # Got partial response before error
            log(f"\nStream interrupted: {e}")
        else:
            return {"status": "error", "error": f"Stream error: {str(e)}"}

    # Print newline after streaming output
    print("", file=sys.stderr)

    if full_content:
        return {
            "status": "success",
            "model": model_name,
            "response": full_content,
            "finish_reason": finish_reason or "stop",
            "streamed": True,
        }
    else:
        return {"status": "error", "error": "No content received from stream"}


def main():
    parser = argparse.ArgumentParser(
        description="Chat with ASI:One — Fetch.ai's agentic language model.",
        epilog=(
            "Examples:\n"
            "  python3 asi1_chat.py --prompt 'What is Fetch.ai?'\n"
            "  python3 asi1_chat.py --prompt 'Write a haiku' --system 'You are a poet'\n"
            "  python3 asi1_chat.py --prompt 'Explain quantum computing' --stream\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--prompt", "-p", required=True,
        help="User message / prompt",
    )
    parser.add_argument(
        "--model", "-m", default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--system", "-s",
        help="System prompt (sets the AI's role/behavior)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=1024,
        help="Maximum tokens in response (default: 1024)",
    )
    parser.add_argument(
        "--temperature", "-t", type=float, default=0.7,
        help="Sampling temperature 0.0-2.0 (default: 0.7, lower=more focused)",
    )
    parser.add_argument(
        "--stream", action="store_true",
        help="Stream response tokens in real-time (printed to stderr)",
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

    result = chat_completion(
        api_key=api_key,
        prompt=args.prompt,
        model=args.model,
        system=args.system,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        stream=args.stream,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
