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
Unit tests for agentverse-skills — no API credentials or network access needed.

Tests parsing logic, code generation, and validation functions in isolation.

Run with:
    python3 tests/test_unit.py
    python3 -m pytest tests/test_unit.py -v
"""

import json
import os
import sys
import unittest

# Add skills/_common to path so we can import the shared module
_COMMON_DIR = os.path.join(os.path.dirname(__file__), "..", "skills", "_common")
sys.path.insert(0, _COMMON_DIR)

try:
    from agentverse_relay import (
        _is_relay_agent,
        extract_results,
        extract_status,
        parse_result_entry,
        RELAY_AGENT_PREFIX,
    )
    HAS_COMMON_MODULE = True
except ImportError:
    HAS_COMMON_MODULE = False


# ---------------------------------------------------------------------------
# Test parse_result_entry — the multi-stage parser for RESULT: log entries
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_COMMON_MODULE, "Shared module not available")
class TestParseResultEntry(unittest.TestCase):
    """Unit tests for parse_result_entry from agentverse_relay."""

    def test_valid_json(self):
        """Stage 1: Valid JSON should parse directly."""
        raw = '{"type": "text", "text": "Hello world"}'
        result = parse_result_entry(raw)
        self.assertEqual(result["type"], "text")
        self.assertEqual(result["text"], "Hello world")

    def test_python_repr_single_quotes(self):
        """Stage 2: Python repr with single quotes should parse via ast.literal_eval."""
        raw = "{'type': 'text', 'text': 'Hello world'}"
        result = parse_result_entry(raw)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["type"], "text")

    def test_python_repr_with_apostrophes(self):
        """Stage 2: Python repr with apostrophes in values should parse correctly."""
        raw = "{'type': 'text', 'text': \"I'm doing great, thanks!\"}"
        result = parse_result_entry(raw)
        self.assertIsInstance(result, dict)
        self.assertIn("great", result["text"])

    def test_python_repr_with_none_true_false(self):
        """Stage 2: Python repr with None/True/False should parse."""
        raw = "{'type': 'text', 'text': 'hello', 'meta': None, 'active': True}"
        result = parse_result_entry(raw)
        self.assertIsInstance(result, dict)
        self.assertIsNone(result["meta"])
        self.assertTrue(result["active"])

    def test_uuid_stripping(self):
        """Stage 2: UUID('hex') objects in Python repr should be cleaned."""
        raw = (
            "{'type': 'resource', 'resource_id': UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890'), "
            "'resource': {'uri': 'agent-storage://test'}}"
        )
        result = parse_result_entry(raw)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["resource_id"], "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    def test_raw_string_fallback(self):
        """Stage 3: Unparseable strings should be returned as-is."""
        raw = "This is just plain text with no structure"
        result = parse_result_entry(raw)
        self.assertEqual(result, raw)

    def test_nested_json(self):
        """Deeply nested JSON should parse correctly."""
        raw = json.dumps({
            "type": "resource",
            "resource": {
                "uri": "agent-storage://https://agentverse.ai/v1/storage/abc123",
                "metadata": {"mime_type": "image/png", "role": "generated-image"},
            },
        })
        result = parse_result_entry(raw)
        self.assertEqual(result["resource"]["metadata"]["mime_type"], "image/png")

    def test_empty_string(self):
        """Empty string should return as-is."""
        result = parse_result_entry("")
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# Test extract_results — extracting RESULT: entries from log arrays
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_COMMON_MODULE, "Shared module not available")
class TestExtractResults(unittest.TestCase):
    """Unit tests for extract_results from agentverse_relay."""

    def test_extracts_result_entries(self):
        """Should extract only entries starting with RESULT:."""
        logs = [
            {"log_entry": "Starting agent...", "log_timestamp": "2026-04-21T00:00:01"},
            {"log_entry": "RESULT:{\"type\": \"text\", \"text\": \"Hello\"}", "log_timestamp": "2026-04-21T00:00:02"},
            {"log_entry": "CHAT_STATUS:sent", "log_timestamp": "2026-04-21T00:00:03"},
        ]
        results = extract_results(logs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Hello")

    def test_preserves_order(self):
        """Results should be in chronological order."""
        logs = [
            {"log_entry": "RESULT:second", "log_timestamp": "2026-04-21T00:00:02"},
            {"log_entry": "RESULT:first", "log_timestamp": "2026-04-21T00:00:01"},
        ]
        results = extract_results(logs)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "first")
        self.assertEqual(results[1], "second")

    def test_empty_logs(self):
        """Empty logs should return empty list."""
        self.assertEqual(extract_results([]), [])

    def test_no_results(self):
        """Logs without RESULT: entries should return empty list."""
        logs = [
            {"log_entry": "Starting agent...", "log_timestamp": "2026-04-21T00:00:01"},
            {"log_entry": "CHAT_STATUS:sent", "log_timestamp": "2026-04-21T00:00:02"},
        ]
        self.assertEqual(extract_results(logs), [])


# ---------------------------------------------------------------------------
# Test extract_status — extracting latest status from logs
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_COMMON_MODULE, "Shared module not available")
class TestExtractStatus(unittest.TestCase):
    """Unit tests for extract_status from agentverse_relay."""

    def test_extracts_latest_status(self):
        """Should return the most recent status entry."""
        logs = [
            {"log_entry": "CHAT_STATUS:sending", "log_timestamp": "2026-04-21T00:00:01"},
            {"log_entry": "CHAT_STATUS:sent", "log_timestamp": "2026-04-21T00:00:02"},
            {"log_entry": "CHAT_STATUS:response_received", "log_timestamp": "2026-04-21T00:00:03"},
        ]
        self.assertEqual(extract_status(logs, prefix="CHAT_STATUS:"), "response_received")

    def test_custom_prefix(self):
        """Should work with IMAGE_STATUS: prefix."""
        logs = [
            {"log_entry": "IMAGE_STATUS:sending_prompt", "log_timestamp": "2026-04-21T00:00:01"},
            {"log_entry": "IMAGE_STATUS:ack_received", "log_timestamp": "2026-04-21T00:00:02"},
        ]
        self.assertEqual(extract_status(logs, prefix="IMAGE_STATUS:"), "ack_received")

    def test_unknown_when_no_status(self):
        """Should return 'unknown' when no status entries found."""
        logs = [{"log_entry": "Starting agent...", "log_timestamp": "2026-04-21T00:00:01"}]
        self.assertEqual(extract_status(logs), "unknown")


# ---------------------------------------------------------------------------
# Test _is_relay_agent — relay name matching
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_COMMON_MODULE, "Shared module not available")
class TestIsRelayAgent(unittest.TestCase):
    """Unit tests for _is_relay_agent from agentverse_relay."""

    def test_exact_match(self):
        self.assertTrue(_is_relay_agent("agentverse-skills-relay"))

    def test_session_suffix(self):
        self.assertTrue(_is_relay_agent("agentverse-skills-relay-abc12345"))

    def test_non_relay(self):
        self.assertFalse(_is_relay_agent("MyTestAgent"))
        self.assertFalse(_is_relay_agent("Blank Agent"))
        self.assertFalse(_is_relay_agent(""))

    def test_none_input(self):
        self.assertFalse(_is_relay_agent(None))


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
