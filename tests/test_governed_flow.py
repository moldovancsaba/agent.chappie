from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.models import DryRunModelAdapter
from agent_chappie.orchestrator import OrchestrationOptions, run_governed_flow
from agent_chappie.router import RouterThresholds, route_decision
from agent_chappie.tools import ToolRegistry
from agent_chappie.validation import (
    ValidationError,
    parse_json_object,
    validate_decision_record,
    validate_execution_plan,
    validate_structured_task_object,
)


class GovernedFlowTests(unittest.TestCase):
    def test_structured_task_object_is_validated(self) -> None:
        data = parse_json_object(DryRunModelAdapter().draft("Task", "https://example.com"), "StructuredTaskObject")
        validated = validate_structured_task_object(data)
        self.assertEqual(validated["intent"], "analyse")

    def test_execution_plan_is_validated(self) -> None:
        adapter = DryRunModelAdapter()
        sto = validate_structured_task_object(
            parse_json_object(adapter.draft("Task", "https://example.com"), "StructuredTaskObject")
        )
        plan = validate_execution_plan(
            parse_json_object(adapter.write("Task", "https://example.com", sto, []), "ExecutionPlan")
        )
        self.assertEqual(plan["stages"][0]["agent_type"], "retriever")

    def test_decision_record_is_validated(self) -> None:
        adapter = DryRunModelAdapter()
        sto = validate_structured_task_object(
            parse_json_object(adapter.draft("Task", "https://example.com"), "StructuredTaskObject")
        )
        plan = validate_execution_plan(
            parse_json_object(adapter.write("Task", "https://example.com", sto, []), "ExecutionPlan")
        )
        decision = validate_decision_record(
            parse_json_object(adapter.judge("Task", "https://example.com", sto, plan, ["evidence"]), "DecisionRecord")
        )
        self.assertEqual(decision["decision"], "proceed")

    def test_router_returns_revise_for_mid_confidence(self) -> None:
        route = route_decision(
            {
                "decision": "proceed",
                "confidence": 0.6,
                "required_human_review": False,
            },
            thresholds=RouterThresholds(proceed_min_confidence=0.85, revise_min_confidence=0.45),
        )
        self.assertEqual(route, "revise")

    def test_orchestrator_persists_trace_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_governed_flow(
                options=OrchestrationOptions(
                    task="Fetch and summarise an article",
                    url="https://example.com",
                    dry_run=True,
                    trace_base_dir=tmpdir,
                ),
                model_adapter=DryRunModelAdapter(),
                tool_registry=ToolRegistry(
                    fetcher=lambda url: f"Offline stub content fetched from {url}. This page discusses structured outputs."
                ),
            )
            self.assertEqual(result["outcome"]["status"], "complete")
            for path in result["trace_paths"].values():
                self.assertTrue(os.path.exists(path))
            with open(result["trace_paths"]["structured_task_object"], encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["artifact_name"], "structured_task_object")
            self.assertEqual(payload["payload"]["task_id"], "task-dry-run-001")

    def test_validation_rejects_missing_required_field(self) -> None:
        with self.assertRaises(ValidationError):
            validate_structured_task_object({"goal": "missing fields"})


if __name__ == "__main__":
    unittest.main()
