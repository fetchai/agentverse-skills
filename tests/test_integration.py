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
Integration tests for agentverse-skills.

These tests make live API calls to Agentverse and ASI:One.
They require:
  - AGENTVERSE_API_KEY environment variable set
  - ASI_ONE_API_KEY environment variable set (for ASI:One tests)
  - Network access to agentverse.ai and api.asi1.ai

Run with:
    python3 tests/test_integration.py
    python3 -m pytest tests/test_integration.py -v

Each test prints PASS/FAIL and a brief summary. Exit code is 0 if all pass.
"""

import json
import os
import subprocess
import sys
import unittest

# Path to skills root
SKILLS_ROOT = os.path.join(os.path.dirname(__file__), "..", "skills")


def run_skill(script_path: str, args: list, timeout: int = 60) -> dict:
    """Run a skill script and return its JSON output."""
    cmd = [sys.executable, script_path] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=os.environ.copy(),
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error": f"Script returned non-JSON output: {result.stdout[:200]}",
            "stderr": result.stderr[:200],
        }


class TestSearchAgents(unittest.TestCase):
    """Tests for agentverse-search skill."""

    SCRIPT = os.path.join(SKILLS_ROOT, "agentverse-search", "scripts", "search_agents.py")

    def test_keyword_search_returns_results(self):
        """Search by keyword should return at least one result."""
        result = run_skill(self.SCRIPT, ["--query", "image generation", "--limit", "5"])
        self.assertEqual(result.get("status"), "success", msg=f"Search failed: {result}")
        agents = result.get("agents", [])
        self.assertGreater(len(agents), 0, "Expected at least one agent for 'image generation'")
        # Each agent should have an address
        for agent in agents:
            self.assertTrue(agent.get("address", "").startswith("agent1"), "Agent address malformed")

    def test_tags_endpoint_returns_list(self):
        """Tags endpoint should return a non-empty list of tags."""
        result = run_skill(self.SCRIPT, ["--tags"])
        self.assertEqual(result.get("status"), "success", msg=f"Tags failed: {result}")
        tags = result.get("tags", [])
        self.assertGreater(len(tags), 0, "Expected at least one tag")

    def test_protocol_filter_no_error(self):
        """Protocol filter should not return 422/error (previously broken field name).

        Fix: send protocol_digest inside filters object as a list
        (payload['filters'] = {'protocol_digest': [protocol]}) instead of as a
        top-level field which caused 422 'Extra inputs are not permitted'.
        """
        proto = "proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62"
        result = run_skill(self.SCRIPT, ["--protocol", proto, "--limit", "5"])
        error = result.get("error", "")
        # Must NOT get a 422 "Extra inputs are not permitted" error
        self.assertNotIn(
            "extra_forbidden", error.lower(),
            msg=f"Got 422 extra_forbidden — protocol_digest is being sent as top-level field: {error}",
        )
        self.assertNotIn(
            "protocol_digest", error,
            msg=f"API rejected protocol_digest field: {error}",
        )


class TestManageAgents(unittest.TestCase):
    """Tests for agentverse-manage skill."""

    SCRIPT = os.path.join(SKILLS_ROOT, "agentverse-manage", "scripts", "manage_agents.py")

    def test_list_agents_succeeds(self):
        """Listing hosted agents should succeed and return a list."""
        result = run_skill(self.SCRIPT, ["list"])
        self.assertEqual(result.get("status"), "success", msg=f"List failed: {result}")
        self.assertIn("agents", result, "Response missing 'agents' key")
        self.assertIsInstance(result["agents"], list)

    def test_list_running_only(self):
        """--running flag should return a subset of or equal agents to full list."""
        full = run_skill(self.SCRIPT, ["list"])
        running = run_skill(self.SCRIPT, ["list", "--running"])
        self.assertEqual(full.get("status"), "success")
        self.assertEqual(running.get("status"), "success")
        self.assertLessEqual(running.get("total", 0), full.get("total", 0))


class TestASI1Chat(unittest.TestCase):
    """Tests for asi1-chat skill."""

    SCRIPT = os.path.join(SKILLS_ROOT, "asi1-chat", "scripts", "asi1_chat.py")

    @classmethod
    def setUpClass(cls):
        if not os.environ.get("ASI_ONE_API_KEY"):
            raise unittest.SkipTest("ASI_ONE_API_KEY not set — skipping ASI:One tests")

    def test_basic_prompt_returns_text(self):
        """A simple prompt to ASI:One mini should return a text response."""
        result = run_skill(
            self.SCRIPT,
            ["--prompt", "Reply with exactly: INTEGRATION_TEST_OK", "--model", "asi1-mini"],
            timeout=30,
        )
        self.assertEqual(result.get("status"), "success", msg=f"ASI:One chat failed: {result}")
        # asi1-chat returns the text in 'response' field
        content = result.get("response", "")
        self.assertGreater(len(content), 0, "Expected non-empty response in 'response' field")


class TestInspectAgent(unittest.TestCase):
    """Tests for agentverse-inspect skill."""

    SCRIPT = os.path.join(SKILLS_ROOT, "agentverse-inspect", "scripts", "inspect_agent.py")
    # Use Fetch.ai DALL-E 3 agent — verified active
    KNOWN_AGENT = "agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl"

    def test_inspect_known_agent(self):
        """Inspecting a known active agent should return almanac data."""
        result = run_skill(self.SCRIPT, ["--agent", self.KNOWN_AGENT])
        self.assertEqual(result.get("status"), "success", msg=f"Inspect failed: {result}")
        agent = result.get("agent", {})
        self.assertTrue(agent.get("address", "").startswith("agent1"))

    def test_recent_agents(self):
        """Recent agents list should return results."""
        result = run_skill(self.SCRIPT, ["--recent", "--limit", "5"])
        self.assertEqual(result.get("status"), "success", msg=f"Recent agents failed: {result}")


class TestDeployAgent(unittest.TestCase):
    """Tests for agentverse-deploy skill.

    These tests create and then clean up agents. They require enough headroom
    in the account's hosted-agent limit (8 by default).
    """

    DEPLOY_SCRIPT = os.path.join(SKILLS_ROOT, "agentverse-deploy", "scripts", "deploy_agent.py")
    MANAGE_SCRIPT = os.path.join(SKILLS_ROOT, "agentverse-manage", "scripts", "manage_agents.py")
    _deployed_address = None

    def test_deploy_inline_code(self):
        """Deploy a minimal agent from inline code, verify it exists, then delete it."""
        agent_code = (
            '@agent.on_event("startup")\n'
            'async def hi(ctx):\n'
            '    ctx.logger.info("integration-test-ok")\n'
        )
        result = run_skill(
            self.DEPLOY_SCRIPT,
            ["--name", "integration-test-deploy", "--code", agent_code],
            timeout=30,
        )
        # May fail due to agent limit — treat as skip, not failure
        if result.get("status") == "error" and "limit" in result.get("error", "").lower():
            self.skipTest(f"Agent limit reached: {result['error']}")

        self.assertEqual(result.get("status"), "success", msg=f"Deploy failed: {result}")
        address = result.get("address", "")
        self.assertTrue(address.startswith("agent1"), "Deployed agent address malformed")
        self.__class__._deployed_address = address

        # Verify agent appears in list
        list_result = run_skill(self.MANAGE_SCRIPT, ["list"])
        if list_result.get("status") == "success":
            addresses = [a.get("address") for a in list_result.get("agents", [])]
            self.assertIn(address, addresses, "Deployed agent not found in list")

    def tearDown(self):
        """Clean up any deployed test agents."""
        if self.__class__._deployed_address:
            run_skill(
                self.MANAGE_SCRIPT,
                ["delete", "--agent", self.__class__._deployed_address],
                timeout=15,
            )
            self.__class__._deployed_address = None


class TestChatAgent(unittest.TestCase):
    """Tests for agentverse-chat skill.

    These tests require a working relay agent and available computation quota.
    They are marked as slow tests since they involve deploying code and
    waiting for responses.
    """

    SCRIPT = os.path.join(SKILLS_ROOT, "agentverse-chat", "scripts", "agentverse_chat.py")
    # Weather Agent — verified active, responds quickly
    WEATHER_AGENT = "agent1qfvydlgcxrvga2kqjxhj3hpngegtysm2c7uk48ywdue0kgvtc2f5cwhyffv"

    def test_chat_returns_structured_output(self):
        """Chat should return structured JSON even on timeout."""
        result = run_skill(
            self.SCRIPT,
            [
                "--target", self.WEATHER_AGENT,
                "--message", "Hello, what can you do?",
                "--wait", "30",
                "--cleanup",
            ],
            timeout=60,
        )
        # Accept either success or timeout — both are valid structured responses
        self.assertIn(
            result.get("status"), ("success", "timeout"),
            msg=f"Unexpected status: {result}",
        )
        # Should always include target in output
        self.assertEqual(
            result.get("target"), self.WEATHER_AGENT,
            "Output should echo back the target address",
        )
        # On success, should have responses list
        if result["status"] == "success":
            self.assertIsInstance(result.get("responses"), list)
            self.assertGreater(len(result["responses"]), 0)

    def test_chat_timeout_includes_debug_info(self):
        """Timeout response should include log entries for debugging."""
        # Use a very short wait to guarantee timeout
        result = run_skill(
            self.SCRIPT,
            [
                "--target", self.WEATHER_AGENT,
                "--message", "Quick test",
                "--wait", "5",
                "--cleanup",
            ],
            timeout=30,
        )
        if result.get("status") == "timeout":
            self.assertIn("log_entries", result, "Timeout should include log_entries")
            self.assertIn("last_status", result, "Timeout should include last_status")
        # If it actually succeeded in 5s, that's fine too — just pass


class TestImageGenAgent(unittest.TestCase):
    """Tests for agentverse-image-gen skill."""

    SCRIPT = os.path.join(SKILLS_ROOT, "agentverse-image-gen", "scripts", "generate_image.py")

    def test_search_image_agents(self):
        """--search should return a list of image generation agents."""
        result = run_skill(self.SCRIPT, ["--search"], timeout=30)
        self.assertEqual(result.get("status"), "success", msg=f"Search failed: {result}")
        agents = result.get("agents", [])
        self.assertGreater(len(agents), 0, "Expected at least one image gen agent")
        # Should include recommended agent
        self.assertIn("recommended", result, "Should include recommended agent address")

    def test_image_gen_returns_structured_output(self):
        """Image generation should return structured JSON."""
        result = run_skill(
            self.SCRIPT,
            [
                "--prompt", "A simple red circle on white background",
                "--wait", "45",
                "--cleanup",
            ],
            timeout=90,
        )
        # Accept success, timeout, or error — all should be structured
        self.assertIn(
            result.get("status"), ("success", "timeout", "error"),
            msg=f"Unexpected status: {result}",
        )
        # On success, should have image_url
        if result["status"] == "success":
            self.assertTrue(
                result.get("image_url", ""),
                "Success response should include image_url",
            )


class TestManageCleanup(unittest.TestCase):
    """Tests for the cleanup subcommand in manage_agents."""

    SCRIPT = os.path.join(SKILLS_ROOT, "agentverse-manage", "scripts", "manage_agents.py")

    def test_cleanup_returns_structured_output(self):
        """Cleanup should return structured JSON even with nothing to clean."""
        result = run_skill(self.SCRIPT, ["cleanup"], timeout=30)
        self.assertIn(
            result.get("status"), ("success", "partial"),
            msg=f"Cleanup returned unexpected status: {result}",
        )
        self.assertIn("deleted", result, "Cleanup should include 'deleted' list")


if __name__ == "__main__":
    # Run with verbose output by default when executed directly
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
