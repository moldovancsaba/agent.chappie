from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from agent_chappie.models import ModelAdapter
from agent_chappie.router import RouterThresholds, route_decision
from agent_chappie.tools import ToolRegistry
from agent_chappie.traces import TraceStore, utc_now_iso
from agent_chappie.validation import (
    parse_json_object,
    validate_decision_record,
    validate_execution_plan,
    validate_outcome,
    validate_structured_task_object,
)


@dataclass
class OrchestrationOptions:
    task: str
    url: str
    dry_run: bool = False
    max_steps: int = 5
    trace_base_dir: str = "traces"


def run_governed_flow(
    options: OrchestrationOptions,
    model_adapter: ModelAdapter,
    tool_registry: ToolRegistry,
    thresholds: RouterThresholds | None = None,
) -> dict[str, Any]:
    request_id = str(uuid4())
    trace_store = TraceStore(options.trace_base_dir)
    sto = None
    plan = None
    decision_record = None
    request_record = {
        "request_id": request_id,
        "timestamp": utc_now_iso(),
        "task": options.task,
        "url": options.url,
        "run_mode": "dry-run" if options.dry_run else "live-run",
    }
    trace_paths = {"request": trace_store.write_artifact("request", request_record)}

    try:
        sto = validate_structured_task_object(
            parse_json_object(model_adapter.draft(task=options.task, url=options.url), "StructuredTaskObject")
        )
        trace_paths["structured_task_object"] = trace_store.write_artifact("structured_task_object", sto)

        retrieval_evidence = collect_retrieval_evidence(sto, tool_registry, options.url)

        plan = validate_execution_plan(
            parse_json_object(
                model_adapter.write(task=options.task, url=options.url, sto=sto, evidence=retrieval_evidence),
                "ExecutionPlan",
            )
        )
        trace_paths["execution_plan"] = trace_store.write_artifact("execution_plan", plan)

        decision_record = validate_decision_record(
            parse_json_object(
                model_adapter.judge(
                    task=options.task,
                    url=options.url,
                    sto=sto,
                    plan=plan,
                    evidence=retrieval_evidence,
                ),
                "DecisionRecord",
            )
        )
        trace_paths["decision_record"] = trace_store.write_artifact("decision_record", decision_record)

        route = route_decision(decision_record, thresholds)

        if route == "proceed":
            outcome = execute_plan(
                task=options.task,
                url=options.url,
                sto=sto,
                plan=plan,
                evidence=retrieval_evidence,
                model_adapter=model_adapter,
            )
        elif route == "revise":
            outcome = {
                "status": "revise",
                "result": "Decision router requested a plan revision before execution.",
                "insights": list(decision_record["judge_rationale"]),
                "route": route,
                "evidence": retrieval_evidence,
            }
        else:
            outcome = {
                "status": "stop",
                "result": "Decision router stopped execution.",
                "insights": list(decision_record["judge_rationale"]),
                "route": route,
                "evidence": retrieval_evidence,
            }

        validated_outcome = validate_outcome(outcome)
    except Exception as exc:
        validated_outcome = validate_outcome(
            {
                "status": "error",
                "result": str(exc),
                "insights": ["Execution failed before completion."],
                "route": "stop",
                "evidence": [],
            }
        )

    if "structured_task_object" not in trace_paths:
        trace_paths["structured_task_object"] = trace_store.write_artifact(
            "structured_task_object",
            _placeholder_artifact("structured_task_object", validated_outcome["result"]),
        )
    if "execution_plan" not in trace_paths:
        trace_paths["execution_plan"] = trace_store.write_artifact(
            "execution_plan",
            _placeholder_artifact("execution_plan", validated_outcome["result"]),
        )
    if "decision_record" not in trace_paths:
        trace_paths["decision_record"] = trace_store.write_artifact(
            "decision_record",
            _placeholder_artifact("decision_record", validated_outcome["result"]),
        )
    trace_paths["outcome"] = trace_store.write_artifact("outcome", validated_outcome)
    return {
        "request": request_record,
        "structured_task_object": sto,
        "execution_plan": plan,
        "decision_record": decision_record,
        "outcome": validated_outcome,
        "trace_paths": trace_paths,
        "run_mode": request_record["run_mode"],
        "run_id": trace_store.run_id,
    }


def collect_retrieval_evidence(
    sto: dict[str, Any],
    tool_registry: ToolRegistry,
    fallback_url: str,
) -> list[str]:
    if "fetch_url" not in sto["candidate_tools"]:
        return []
    target_url = fallback_url
    content = tool_registry.execute("fetch_url", target_url)
    return [content]


def execute_plan(
    task: str,
    url: str,
    sto: dict[str, Any],
    plan: dict[str, Any],
    evidence: list[str],
    model_adapter: ModelAdapter,
) -> dict[str, Any]:
    raw_outcome = model_adapter.summarize(task=task, url=url, sto=sto, plan=plan, evidence=evidence)
    outcome = parse_json_object(raw_outcome, "Outcome")
    return validate_outcome(outcome)


def _placeholder_artifact(artifact_name: str, reason: str) -> dict[str, str]:
    return {
        "status": "not_produced",
        "artifact": artifact_name,
        "reason": reason,
    }
