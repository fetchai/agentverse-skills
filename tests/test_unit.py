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

import importlib.util
import json
import os
import sys
import unittest

# Add skills/_common to path so we can import the shared module
_COMMON_DIR = os.path.join(os.path.dirname(__file__), "..", "skills", "_common")
sys.path.insert(0, _COMMON_DIR)

try:
    import agentverse_relay
    from agentverse_relay import (
        _is_relay_agent,
        extract_acks,
        extract_results,
        extract_status,
        parse_result_entry,
        RELAY_AGENT_PREFIX,
    )
    HAS_COMMON_MODULE = True
except ImportError:
    HAS_COMMON_MODULE = False


# Two real Agentverse addresses, used as "the agent we asked" vs "some other
# agent whose reply is still sitting in the relay's log buffer".
TARGET_AGENT = "agent1q0utywlfr3dfrfkwk4fjmtdrfew0zh692untdlr877d6ay8ykwpewydmxtl"
OTHER_AGENT = "agent1qd77ueqzd4dug2wt0dxw4r4adu33zws4exy0qlv204qvvna3anprw4zmg5t"

# Run ids as emitted by the relay templates: 8 hex chars.
THIS_RUN = "b17c4d2e"
PRIOR_RUN = "0a9f31cc"


def _load_script_module(skill: str, filename: str):
    """Load a skill script by path — the skill directories are not importable."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "skills", skill, "scripts", filename
    )
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
# Test invocation isolation — a relay's log buffer survives stop/upload/start,
# so results from earlier runs are still sitting there when we poll (#41).
# ---------------------------------------------------------------------------

def _result_line(run_id: str, sender: str, payload) -> str:
    """Build a RESULT: log line exactly as the relay templates emit them."""
    return "RESULT:" + run_id + ":" + sender + ":" + str(payload)


@unittest.skipUnless(HAS_COMMON_MODULE, "Shared module not available")
class TestInvocationIsolation(unittest.TestCase):
    """Results from other invocations must not be returned as this one's answer."""

    def test_stale_unattributed_result_rejected(self):
        """A legacy RESULT: left by an earlier run must not answer this one (#41).

        This is the reported failure: the relay holds a two-day-old reply, this
        run has sent its message but nothing has come back yet, and the caller
        gets the old reply in ~5s.
        """
        logs = [
            {"log_entry": "RESULT:{'type': 'text', 'text': 'answer from two days ago'}",
             "log_timestamp": "2026-08-02T09:15:00"},
            {"log_entry": "CHAT_STATUS:sending", "log_timestamp": "2026-08-04T11:00:01"},
            {"log_entry": "CHAT_STATUS:sent", "log_timestamp": "2026-08-04T11:00:02"},
        ]
        results = extract_results(
            logs, since="2026-08-04T11:00:00", run_id=THIS_RUN, expected_sender=TARGET_AGENT
        )
        self.assertEqual(results, [])

    def test_stale_attributed_result_rejected(self):
        """A RESULT: carrying an earlier run's id must not answer this one."""
        logs = [
            {"log_entry": _result_line(PRIOR_RUN, TARGET_AGENT, {"type": "text", "text": "old"}),
             "log_timestamp": "2026-08-02T09:15:00"},
            {"log_entry": "CHAT_STATUS:sending", "log_timestamp": "2026-08-04T11:00:01"},
            {"log_entry": "CHAT_STATUS:sent", "log_timestamp": "2026-08-04T11:00:02"},
        ]
        self.assertEqual(extract_results(logs, run_id=THIS_RUN), [])

    def test_correlation_mismatch_rejected_inside_time_window(self):
        """A different run id is rejected even when the entry is recent.

        Concurrent invocations sharing a relay land inside each other's
        timestamp window, so the run id — not the clock — has to decide.
        """
        logs = [
            {"log_entry": _result_line(PRIOR_RUN, TARGET_AGENT, {"type": "text", "text": "not ours"}),
             "log_timestamp": "2026-08-04T11:00:07"},
        ]
        results = extract_results(
            logs, since="2026-08-04T11:00:00", run_id=THIS_RUN, expected_sender=TARGET_AGENT
        )
        self.assertEqual(results, [])

    def test_wrong_sender_rejected(self):
        """A reply from an agent we did not ask must not be returned as its answer."""
        logs = [
            {"log_entry": _result_line(THIS_RUN, OTHER_AGENT, {"type": "text", "text": "wrong agent"}),
             "log_timestamp": "2026-08-04T11:00:07"},
        ]
        self.assertEqual(
            extract_results(logs, run_id=THIS_RUN, expected_sender=TARGET_AGENT), []
        )

    def test_current_result_accepted(self):
        """A reply carrying this run's id and the requested sender is returned."""
        logs = [
            {"log_entry": "CHAT_STATUS:sent", "log_timestamp": "2026-08-04T11:00:02"},
            {"log_entry": _result_line(THIS_RUN, TARGET_AGENT, {"type": "text", "text": "hello back"}),
             "log_timestamp": "2026-08-04T11:00:07"},
        ]
        results = extract_results(
            logs, since="2026-08-04T11:00:00", run_id=THIS_RUN, expected_sender=TARGET_AGENT
        )
        self.assertEqual(results, [{"type": "text", "text": "hello back"}])

    def test_since_excludes_entries_at_or_before_watermark(self):
        """The timestamp cutoff is a second guard: it drops replayed entries.

        ``since`` is the newest timestamp the relay had logged before this run
        started, so anything at or before it predates us.
        """
        logs = [
            {"log_entry": _result_line(THIS_RUN, TARGET_AGENT, {"type": "text", "text": "before"}),
             "log_timestamp": "2026-08-04T11:00:00"},
            {"log_entry": _result_line(THIS_RUN, TARGET_AGENT, {"type": "text", "text": "after"}),
             "log_timestamp": "2026-08-04T11:00:07"},
        ]
        results = extract_results(logs, since="2026-08-04T11:00:00", run_id=THIS_RUN)
        self.assertEqual(results, [{"type": "text", "text": "after"}])

    def test_defaults_unchanged(self):
        """With no filters the extractor behaves exactly as before."""
        logs = [
            {"log_entry": "RESULT:{'type': 'text', 'text': 'old'}",
             "log_timestamp": "2026-08-02T09:15:00"},
            {"log_entry": "CHAT_STATUS:sent", "log_timestamp": "2026-08-04T11:00:02"},
        ]
        self.assertEqual(extract_results(logs), [{"type": "text", "text": "old"}])

    def test_attribution_stripped_from_payload(self):
        """Attribution is metadata — callers still get the bare content dict."""
        logs = [
            {"log_entry": _result_line(THIS_RUN, TARGET_AGENT, {"type": "text", "text": "hi"}),
             "log_timestamp": "2026-08-04T11:00:07"},
        ]
        self.assertEqual(extract_results(logs), [{"type": "text", "text": "hi"}])

    def test_resource_payload_survives_attribution(self):
        """A ResourceContent payload still parses through the three-stage parser."""
        payload = {
            "type": "resource",
            "resource": {
                "uri": "agent-storage://https://agentverse.ai/v1/storage/abc123",
                "metadata": {"mime_type": "image/png"},
            },
        }
        logs = [
            {"log_entry": _result_line(THIS_RUN, TARGET_AGENT, payload),
             "log_timestamp": "2026-08-04T11:00:07"},
        ]
        results = extract_results(logs, run_id=THIS_RUN, expected_sender=TARGET_AGENT)
        self.assertEqual(results[0]["resource"]["metadata"]["mime_type"], "image/png")

    def test_latest_log_timestamp(self):
        """The pre-run watermark is the newest timestamp already in the buffer."""
        logs = [
            {"log_entry": "CHAT_STATUS:sent", "log_timestamp": "2026-08-02T09:15:00"},
            {"log_entry": "RESULT:{}", "log_timestamp": "2026-08-02T09:15:04"},
        ]
        self.assertEqual(agentverse_relay.latest_log_timestamp(logs), "2026-08-02T09:15:04")
        self.assertEqual(agentverse_relay.latest_log_timestamp([]), "")


# ---------------------------------------------------------------------------
# Test extract_result_entries — the incremental seam used by the image-gen
# polling loop, which needs a dedup key alongside each parsed payload (#20)
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_COMMON_MODULE, "Shared module not available")
class TestExtractResultEntries(unittest.TestCase):
    """Unit tests for extract_result_entries from agentverse_relay."""

    def test_first_poll_ignores_pre_existing_history(self):
        """History must not be classified as new on the first poll.

        The image-gen loop starts with an empty ``seen_entries`` set, so on the
        first poll every entry in the buffer looks new — including a previous
        run's image resource.
        """
        stale_image = {
            "type": "resource",
            "resource": {"uri": "agent-storage://https://agentverse.ai/v1/storage/old"},
        }
        logs = [
            {"log_entry": _result_line(PRIOR_RUN, TARGET_AGENT, stale_image),
             "log_timestamp": "2026-08-02T09:15:04"},
            {"log_entry": "IMAGE_STATUS:prompt_sent", "log_timestamp": "2026-08-04T11:00:02"},
        ]
        entries = agentverse_relay.extract_result_entries(
            logs, since="2026-08-04T11:00:00", run_id=THIS_RUN, expected_sender=TARGET_AGENT
        )
        self.assertEqual(entries, [])

    def test_returns_dedup_key_with_payload(self):
        """Each accepted entry comes back as (dedup_key, parsed_payload)."""
        logs = [
            {"log_entry": _result_line(THIS_RUN, TARGET_AGENT, {"type": "text", "text": "one"}),
             "log_timestamp": "2026-08-04T11:00:07"},
        ]
        entries = agentverse_relay.extract_result_entries(logs, run_id=THIS_RUN)
        self.assertEqual(len(entries), 1)
        key, payload = entries[0]
        self.assertIn("2026-08-04T11:00:07", key)
        self.assertEqual(payload, {"type": "text", "text": "one"})

    def test_same_timestamp_entries_get_distinct_keys(self):
        """Two entries logged in the same instant must not collide (#20)."""
        logs = [
            {"log_entry": _result_line(THIS_RUN, TARGET_AGENT, {"type": "text", "text": "generating"}),
             "log_timestamp": "2026-08-04T11:00:07"},
            {"log_entry": _result_line(THIS_RUN, TARGET_AGENT, {
                "type": "resource",
                "resource": {"uri": "agent-storage://https://agentverse.ai/v1/storage/new"},
            }), "log_timestamp": "2026-08-04T11:00:07"},
        ]
        entries = agentverse_relay.extract_result_entries(logs, run_id=THIS_RUN)
        keys = [key for key, _payload in entries]
        self.assertEqual(len(entries), 2)
        self.assertEqual(len(set(keys)), 2)


# ---------------------------------------------------------------------------
# Test the relay templates — the uploaded code is what produces the log lines
# the extractor consumes, so the two have to agree
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_COMMON_MODULE, "Shared module not available")
class TestRelayCodeAttribution(unittest.TestCase):
    """The generated relay code must attribute what it logs."""

    def test_chat_code_round_trips_through_extractor(self):
        """A line the chat relay would log is accepted by the strict extractor."""
        chat = _load_script_module("agentverse-chat", "agentverse_chat.py")
        code = chat.build_chat_code(TARGET_AGENT, "Hello", run_id=THIS_RUN)
        self.assertIn(f'RUN_ID = "{THIS_RUN}"', code)
        self.assertIn('"RESULT:" + RUN_ID + ":" + sender + ":"', code)

        logged = _result_line(THIS_RUN, TARGET_AGENT, {"type": "text", "text": "Hi"})
        logs = [{"log_entry": logged, "log_timestamp": "2026-08-04T11:00:07"}]
        self.assertEqual(
            extract_results(logs, run_id=THIS_RUN, expected_sender=TARGET_AGENT),
            [{"type": "text", "text": "Hi"}],
        )

    def test_chat_ack_keeps_sender_and_msg_id(self):
        """handle_ack must log who acknowledged what, not just that it happened."""
        chat = _load_script_module("agentverse-chat", "agentverse_chat.py")
        code = chat.build_chat_code(TARGET_AGENT, "Hello", run_id=THIS_RUN)
        self.assertIn("msg.acknowledged_msg_id", code)
        self.assertIn('"CHAT_ACK:" + RUN_ID + ":" + sender + ":"', code)

    def test_image_gen_code_attributes_results(self):
        """The image-gen relay tags its RESULT: lines the same way."""
        image_gen = _load_script_module("agentverse-image-gen", "generate_image.py")
        code = image_gen.build_image_gen_code(TARGET_AGENT, "a dragon", run_id=THIS_RUN)
        self.assertIn(f'RUN_ID = "{THIS_RUN}"', code)
        self.assertIn('"RESULT:" + RUN_ID + ":" + sender + ":"', code)


# ---------------------------------------------------------------------------
# Test the call sites — the filters above are only worth anything if the
# scripts actually pass them, and if the relay is named per invocation.
# ---------------------------------------------------------------------------

def _stub_network(module, logs, relay_name_sink=None):
    """Replace a script's network calls with a fixed log buffer.

    Returns a dict that collects the run_id and msg_id the script embedded in
    the uploaded relay code, so a test can build correctly attributed entries.
    """
    seen = {}
    clock = {"t": 0}

    def fake_upload(api_key, address, code):
        for line in code.splitlines():
            if line.startswith('RUN_ID = "'):
                seen["run_id"] = line.split('"')[1]
            elif line.startswith('MSG_ID = "'):
                seen["msg_id"] = line.split('"')[1]
        return True

    def fake_find_or_create(api_key, session_id=None):
        if relay_name_sink is not None:
            relay_name_sink.append(session_id)
        return "agent1qrelay"

    module.get_api_key = lambda: "fake-key"
    module.find_or_create_relay = fake_find_or_create
    module.stop_agent = lambda k, a: None
    module.start_agent = lambda k, a: True
    module.upload_code = fake_upload
    module.delete_agent = lambda k, a: True
    module.get_logs = lambda k, a: list(logs(seen) if callable(logs) else logs)
    module.time.sleep = lambda s: clock.__setitem__("t", clock["t"] + 1)
    module.log = lambda m: None
    return seen


@unittest.skipUnless(HAS_COMMON_MODULE, "Shared module not available")
class TestCallSiteWiring(unittest.TestCase):
    """Each script must pass the isolation arguments, not merely have them."""

    STALE_IMAGE = (
        "{'type': 'resource', 'resource': {'uri': "
        "'agent-storage://https://agentverse.ai/v1/storage/OLD-IMAGE', "
        "'metadata': {'mime_type': 'image/png'}}}"
    )

    def test_image_gen_ignores_prior_run_image_on_first_poll(self):
        """The dedup set starts empty, so history must be excluded by filter."""
        image_gen = _load_script_module("agentverse-image-gen", "generate_image.py")
        logs = [{"log_entry": _result_line(PRIOR_RUN, TARGET_AGENT, self.STALE_IMAGE),
                 "log_timestamp": "2026-07-28T09:15:04"}]
        _stub_network(image_gen, logs)
        result = image_gen.generate_image(
            api_key="fake", prompt="a blue whale", target=TARGET_AGENT,
            wait=10, relay="agent1qrelay",
        )
        self.assertNotEqual(result["status"], "success")
        self.assertIsNone(result.get("image_url"))

    def test_chat_relay_is_named_for_this_invocation(self):
        """Concurrent runs must not share a relay (#14)."""
        chat = _load_script_module("agentverse-chat", "agentverse_chat.py")
        session_ids = []
        seen = _stub_network(chat, [], relay_name_sink=session_ids)
        chat.run_chat(target=TARGET_AGENT, message="Hello", wait=5, relay=None)
        self.assertEqual(session_ids, [seen["run_id"]])

    def test_image_gen_relay_is_named_for_this_invocation(self):
        image_gen = _load_script_module("agentverse-image-gen", "generate_image.py")
        session_ids = []
        seen = _stub_network(image_gen, [], relay_name_sink=session_ids)
        image_gen.generate_image(
            api_key="fake", prompt="a dragon", target=TARGET_AGENT,
            wait=5, relay=None,
        )
        self.assertEqual(session_ids, [seen["run_id"]])

    def test_timeout_diagnostics_exclude_earlier_runs(self):
        """The timeout dump must not pad this run with another run's lines."""
        chat = _load_script_module("agentverse-chat", "agentverse_chat.py")
        logs = [
            {"log_entry": "CHAT_STATUS:response_received",
             "log_timestamp": "2026-08-02T09:15:03"},
            {"log_entry": _result_line(PRIOR_RUN, TARGET_AGENT,
                                       {"type": "text", "text": "old"}),
             "log_timestamp": "2026-08-02T09:15:04"},
        ]
        _stub_network(chat, logs)
        result = chat.run_chat(target=TARGET_AGENT, message="Hello",
                               wait=10, relay="agent1qrelay")
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["log_entries"], [])
        self.assertNotEqual(result["last_status"], "response_received")

    def test_timeout_reports_whether_target_acknowledged(self):
        """An ack for this run's msg_id is reported, and never gates the run."""
        chat = _load_script_module("agentverse-chat", "agentverse_chat.py")

        def logs(seen):
            if "msg_id" not in seen:
                return []
            return [{"log_entry": _ack_line(seen["run_id"], TARGET_AGENT, seen["msg_id"]),
                     "log_timestamp": "2026-08-04T11:00:02"}]

        _stub_network(chat, logs)
        result = chat.run_chat(target=TARGET_AGENT, message="Hello",
                               wait=10, relay="agent1qrelay")
        self.assertEqual(result["status"], "timeout")
        self.assertTrue(result["acknowledged"])

    def test_prior_run_ack_is_not_reported_as_ours(self):
        chat = _load_script_module("agentverse-chat", "agentverse_chat.py")

        def logs(seen):
            if "msg_id" not in seen:
                return []
            return [{"log_entry": _ack_line(PRIOR_RUN, TARGET_AGENT, seen["msg_id"]),
                     "log_timestamp": "2026-08-04T11:00:02"}]

        _stub_network(chat, logs)
        result = chat.run_chat(target=TARGET_AGENT, message="Hello",
                               wait=10, relay="agent1qrelay")
        self.assertFalse(result["acknowledged"])


# ---------------------------------------------------------------------------
# Test extract_acks — correlating acknowledgements to this invocation
# ---------------------------------------------------------------------------

MSG_ID = "3f6b1c90-6d1a-4a3e-9a44-4d1f0f1c2b77"
OTHER_MSG_ID = "11111111-2222-3333-4444-555555555555"


def _ack_line(run_id, sender, acked_msg_id):
    """A CHAT_ACK: line exactly as the relay template writes it."""
    return f"CHAT_ACK:{run_id}:{sender}:{acked_msg_id}"


@unittest.skipUnless(HAS_COMMON_MODULE, "Shared module not available")
class TestExtractAcks(unittest.TestCase):
    """Acknowledgements are correlated the same way results are."""

    def test_ack_from_this_run_accepted(self):
        logs = [{"log_entry": _ack_line(THIS_RUN, TARGET_AGENT, MSG_ID),
                 "log_timestamp": "2026-08-04T11:00:05"}]
        self.assertEqual(
            extract_acks(logs, run_id=THIS_RUN, expected_sender=TARGET_AGENT),
            [MSG_ID],
        )

    def test_ack_from_prior_run_rejected(self):
        logs = [{"log_entry": _ack_line(PRIOR_RUN, TARGET_AGENT, MSG_ID),
                 "log_timestamp": "2026-08-02T09:15:04"}]
        self.assertEqual(
            extract_acks(logs, run_id=THIS_RUN, expected_sender=TARGET_AGENT), []
        )

    def test_ack_from_other_agent_rejected(self):
        logs = [{"log_entry": _ack_line(THIS_RUN, OTHER_AGENT, MSG_ID),
                 "log_timestamp": "2026-08-04T11:00:05"}]
        self.assertEqual(
            extract_acks(logs, run_id=THIS_RUN, expected_sender=TARGET_AGENT), []
        )

    def test_since_excludes_earlier_acks(self):
        logs = [{"log_entry": _ack_line(THIS_RUN, TARGET_AGENT, MSG_ID),
                 "log_timestamp": "2026-08-04T11:00:05"}]
        self.assertEqual(
            extract_acks(logs, since="2026-08-04T11:00:05",
                         run_id=THIS_RUN, expected_sender=TARGET_AGENT),
            [],
        )

    def test_unattributed_ack_rejected(self):
        """No legacy CHAT_ACK: shape exists, so an unattributed one is not ours."""
        logs = [{"log_entry": f"CHAT_ACK:{MSG_ID}",
                 "log_timestamp": "2026-08-04T11:00:05"}]
        self.assertEqual(extract_acks(logs, run_id=THIS_RUN), [])

    def test_result_lines_are_not_acks(self):
        logs = [{"log_entry": _result_line(THIS_RUN, TARGET_AGENT,
                                           {"type": "text", "text": "Hi"}),
                 "log_timestamp": "2026-08-04T11:00:07"}]
        self.assertEqual(extract_acks(logs, run_id=THIS_RUN), [])

    def test_mismatched_msg_id_is_visible_to_caller(self):
        """The ack is for a different message, so the caller must not match it."""
        logs = [{"log_entry": _ack_line(THIS_RUN, TARGET_AGENT, OTHER_MSG_ID),
                 "log_timestamp": "2026-08-04T11:00:05"}]
        acked = extract_acks(logs, run_id=THIS_RUN, expected_sender=TARGET_AGENT)
        self.assertEqual(acked, [OTHER_MSG_ID])
        self.assertNotIn(MSG_ID, acked)


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
