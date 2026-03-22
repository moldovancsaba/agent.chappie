from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent_chappie.models import ModelClient
from agent_chappie.tools import ToolRegistry


ALLOWED_STATUSES = {"complete", "error", "continue"}


@dataclass
class AgentResult:
    payload: dict[str, Any]
    steps: int


def expected_schema() -> dict[str, object]:
    return {
        "status": ["complete", "error", "continue"],
        "result": "string",
        "next_action": "string",
    }


def validate_payload(data: dict[str, Any]) -> tuple[bool, str]:
    status = data.get("status")
    result = data.get("result")
    next_action = data.get("next_action", "")

    if status not in ALLOWED_STATUSES:
        return False, "invalid_status"
    if not isinstance(result, str):
        return False, "missing_result"
    if not isinstance(next_action, str):
        return False, "invalid_next_action"
    if status == "continue" and not next_action:
        return False, "missing_next_action"
    return True, ""


def build_initial_prompt(task: str, url: str | None = None) -> str:
    if url:
        return (
            f"Task: {task}\n"
            f"Candidate URL: {url}\n"
            "Return JSON with status, result, next_action, and input if a tool is needed."
        )
    return f"Task: {task}\nReturn JSON with status, result, next_action, and input if a tool is needed."


def build_followup_prompt(task: str, tool_name: str, tool_input: str, tool_output: str) -> str:
    return (
        f"Task: {task}\n"
        f"tool_name: {tool_name}\n"
        f"tool_input: {tool_input}\n"
        f"tool_result: {tool_output}\n"
        "Use the tool result to finish the task. Return JSON only."
    )


def run_task(
    task: str,
    model_client: ModelClient,
    tool_registry: ToolRegistry,
    max_steps: int = 5,
    url: str | None = None,
) -> AgentResult:
    prompt = build_initial_prompt(task, url=url)

    for step in range(1, max_steps + 1):
        raw_output = model_client.generate(prompt)

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            return AgentResult(payload={"status": "invalid_json", "raw_output": raw_output}, steps=step)

        is_valid, error_code = validate_payload(data)
        if not is_valid:
            invalid_payload = {"status": "schema_error", "error": error_code, "data": data}
            return AgentResult(payload=invalid_payload, steps=step)

        if data["status"] in {"complete", "error"}:
            return AgentResult(payload=data, steps=step)

        tool_name = data["next_action"]
        tool_input = data.get("input") or url
        if not isinstance(tool_input, str) or not tool_input:
            return AgentResult(
                payload={"status": "tool_input_error", "error": "missing_input", "data": data},
                steps=step,
            )

        try:
            tool_output = tool_registry.execute(tool_name, tool_input)
        except Exception as exc:
            return AgentResult(
                payload={
                    "status": "tool_error",
                    "error": str(exc),
                    "tool": tool_name,
                    "input": tool_input,
                },
                steps=step,
            )

        prompt = build_followup_prompt(task, tool_name, tool_input, tool_output)

    return AgentResult(payload={"status": "max_iterations_reached"}, steps=max_steps)
