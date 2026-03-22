from __future__ import annotations

import json
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.agent_loop import expected_schema, run_task, validate_payload
from agent_chappie.models import StubSequenceClient
from agent_chappie.tools import ToolRegistry


class AgentLoopTests(unittest.TestCase):
    def test_expected_schema_shape(self) -> None:
        schema = expected_schema()
        self.assertEqual(schema["result"], "string")
        self.assertIn("continue", schema["status"])

    def test_validate_payload_accepts_complete(self) -> None:
        is_valid, error = validate_payload(
            {"status": "complete", "result": "done", "next_action": ""}
        )
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validate_payload_rejects_missing_next_action_on_continue(self) -> None:
        is_valid, error = validate_payload({"status": "continue", "result": "keep going"})
        self.assertFalse(is_valid)
        self.assertEqual(error, "missing_next_action")

    def test_run_task_rejects_invalid_json(self) -> None:
        model = StubSequenceClient(outputs=["not json"])
        registry = ToolRegistry(fetcher=lambda _: "ignored")
        result = run_task("demo", model, registry)
        self.assertEqual(result.payload["status"], "invalid_json")
        self.assertEqual(result.steps, 1)

    def test_run_task_executes_tool_and_completes(self) -> None:
        outputs = [
            json.dumps(
                {
                    "status": "continue",
                    "result": "need content",
                    "next_action": "fetch_url",
                    "input": "https://example.com",
                }
            ),
            json.dumps(
                {
                    "status": "complete",
                    "result": "summary",
                    "next_action": "",
                    "insights": ["a", "b"],
                }
            ),
        ]
        model = StubSequenceClient(outputs=outputs)
        registry = ToolRegistry(fetcher=lambda url: f"content from {url}")
        result = run_task("demo", model, registry)
        self.assertEqual(result.payload["status"], "complete")
        self.assertEqual(result.steps, 2)

    def test_run_task_stops_at_max_steps(self) -> None:
        outputs = [
            json.dumps(
                {
                    "status": "continue",
                    "result": "loop",
                    "next_action": "fetch_url",
                    "input": "https://example.com",
                }
            )
            for _ in range(3)
        ]
        model = StubSequenceClient(outputs=outputs)
        registry = ToolRegistry(fetcher=lambda _: "content")
        result = run_task("demo", model, registry, max_steps=3)
        self.assertEqual(result.payload["status"], "max_iterations_reached")
        self.assertEqual(result.steps, 3)


if __name__ == "__main__":
    unittest.main()
