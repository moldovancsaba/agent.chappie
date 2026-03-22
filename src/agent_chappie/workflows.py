from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_chappie.models import DryRunModelAdapter, ModelAdapter, OllamaClient, OllamaModelAdapter
from agent_chappie.orchestrator import OrchestrationOptions, run_governed_flow
from agent_chappie.tools import ToolRegistry


@dataclass
class WorkflowOptions:
    task: str
    url: str
    dry_run: bool = False
    max_steps: int = 5
    trace_base_dir: str = "traces"


def build_model_adapter(dry_run: bool = False) -> ModelAdapter:
    if dry_run:
        return DryRunModelAdapter()
    return OllamaModelAdapter(client=OllamaClient())


def build_tool_registry(dry_run: bool = False) -> ToolRegistry:
    if dry_run:
        return ToolRegistry(
            fetcher=lambda url: f"Offline stub content fetched from {url}. This page discusses structured outputs."
        )
    return ToolRegistry()


def run_article_summary_workflow(options: WorkflowOptions) -> dict[str, Any]:
    model_adapter = build_model_adapter(options.dry_run)
    tool_registry = build_tool_registry(options.dry_run)
    result = run_governed_flow(
        options=OrchestrationOptions(
            task=options.task,
            url=options.url,
            dry_run=options.dry_run,
            max_steps=options.max_steps,
            trace_base_dir=options.trace_base_dir,
        ),
        model_adapter=model_adapter,
        tool_registry=tool_registry,
    )
    return {
        "workflow": "article_summary",
        "task": options.task,
        "url": options.url,
        "run_mode": result["run_mode"],
        "output": result["outcome"],
        "artifacts": {
            "request": result["request"],
            "structured_task_object": result["structured_task_object"],
            "execution_plan": result["execution_plan"],
            "decision_record": result["decision_record"],
        },
        "trace_paths": result["trace_paths"],
    }
