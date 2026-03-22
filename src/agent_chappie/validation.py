from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_chappie.contract_schemas import (
    DECISION_SUMMARY_SCHEMA,
    FEEDBACK_PAYLOAD_SCHEMA,
    FEEDBACK_SCHEMA,
    JOB_REQUEST_ARTIFACT_SCHEMA,
    JOB_REQUEST_INPUT_PAYLOAD_SCHEMA,
    JOB_REQUEST_SCHEMA,
    JOB_RESULT_BLOCKED_PAYLOAD_SCHEMA,
    JOB_RESULT_COMPLETE_PAYLOAD_SCHEMA,
    JOB_RESULT_SCHEMA,
    SYSTEM_OBSERVATION_SCHEMA,
    TASK_SCHEMA,
)
from agent_chappie.schemas import (
    DECISION_COMPONENTS_SCHEMA,
    DECISION_RECORD_SCHEMA,
    EXECUTION_PLAN_SCHEMA,
    EXECUTION_STAGE_SCHEMA,
    OUTCOME_SCHEMA,
    STRUCTURED_TASK_OBJECT_SCHEMA,
)


class ValidationError(ValueError):
    """Raised when JSON parsing or schema validation fails."""


def parse_json_object(raw_output: str, artifact_name: str) -> dict[str, Any]:
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{artifact_name} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{artifact_name} must be a JSON object")
    return data


def validate_structured_task_object(data: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(data, STRUCTURED_TASK_OBJECT_SCHEMA, "StructuredTaskObject")
    _validate_string_list("constraints", data["constraints"])
    _validate_string_list("candidate_tools", data["candidate_tools"])
    _validate_string_list("candidate_domains", data["candidate_domains"])
    _validate_string_list("success_criteria", data["success_criteria"])
    _validate_confidence("draft_confidence", data["draft_confidence"])
    return data


def validate_execution_plan(data: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(data, EXECUTION_PLAN_SCHEMA, "ExecutionPlan")
    _validate_string_list("required_evidence", data["required_evidence"])
    _validate_string_list("acceptance_tests", data["acceptance_tests"])
    _validate_confidence("writer_confidence", data["writer_confidence"])
    for index, stage in enumerate(data["stages"]):
        if not isinstance(stage, dict):
            raise ValidationError(f"ExecutionPlan stage {index} must be an object")
        _validate_schema(stage, EXECUTION_STAGE_SCHEMA, f"ExecutionPlan stage {index}")
        _validate_string_list("inputs", stage["inputs"])
        _validate_string_list("outputs", stage["outputs"])
        _validate_string_list("depends_on", stage["depends_on"])
        _validate_string_list("tool_calls_allowed", stage["tool_calls_allowed"])
    return data


def validate_decision_record(data: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(data, DECISION_RECORD_SCHEMA, "DecisionRecord")
    if not isinstance(data["confidence_components"], dict):
        raise ValidationError("DecisionRecord confidence_components must be an object")
    _validate_schema(data["confidence_components"], DECISION_COMPONENTS_SCHEMA, "DecisionRecord confidence_components")
    _validate_string_list("risk_flags", data["risk_flags"])
    _validate_string_list("judge_rationale", data["judge_rationale"])
    _validate_confidence("confidence", data["confidence"])
    for field_name in DECISION_COMPONENTS_SCHEMA:
        _validate_confidence(field_name, data["confidence_components"][field_name])
    return data


def validate_outcome(data: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(data, OUTCOME_SCHEMA, "Outcome")
    _validate_string_list("insights", data["insights"])
    if not isinstance(data["evidence"], list):
        raise ValidationError("Outcome evidence must be a list")
    return data


def validate_job_request(data: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(data, JOB_REQUEST_SCHEMA, "JobRequest")
    _validate_non_empty_string("job_id", data["job_id"])
    _validate_non_empty_string("app_id", data["app_id"])
    _validate_non_empty_string("project_id", data["project_id"])
    _validate_non_empty_string("requested_capability", data["requested_capability"])
    _validate_iso8601_timestamp("submitted_at", data["submitted_at"])
    _validate_optional_iso8601_timestamp("deadline_at", data.get("deadline_at"))
    _validate_optional_non_empty_string("requested_by", data.get("requested_by"))
    _validate_optional_non_empty_string("trace_parent_id", data.get("trace_parent_id"))
    _validate_optional_string_list("source_refs", data.get("source_refs"))
    _validate_optional_string_list("policy_tags", data.get("policy_tags"))

    if not isinstance(data["input_payload"], dict):
        raise ValidationError("JobRequest input_payload must be an object")
    _validate_schema(data["input_payload"], JOB_REQUEST_INPUT_PAYLOAD_SCHEMA, "JobRequest input_payload")
    _validate_non_empty_string("prompt", data["input_payload"]["prompt"])

    artifacts = data["input_payload"]["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise ValidationError("JobRequest input_payload artifacts must be a non-empty list")
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise ValidationError(f"JobRequest input_payload artifact {index} must be an object")
        _validate_schema(artifact, JOB_REQUEST_ARTIFACT_SCHEMA, f"JobRequest input_payload artifact {index}")
    return data


def validate_system_observation(data: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(data, SYSTEM_OBSERVATION_SCHEMA, "SystemObservation")
    _validate_non_empty_string("signal_id", data["signal_id"])
    _validate_non_empty_string("competitor", data["competitor"])
    _validate_non_empty_string("region", data["region"])
    _validate_non_empty_string("summary", data["summary"])
    _validate_non_empty_string("source_ref", data["source_ref"])
    _validate_iso8601_timestamp("observed_at", data["observed_at"])
    _validate_confidence("confidence", data["confidence"])
    return data


def validate_job_result(data: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(data, JOB_RESULT_SCHEMA, "JobResult")
    _validate_non_empty_string("job_id", data["job_id"])
    _validate_non_empty_string("app_id", data["app_id"])
    _validate_non_empty_string("project_id", data["project_id"])
    _validate_iso8601_timestamp("completed_at", data["completed_at"])

    if not isinstance(data["result_payload"], dict):
        raise ValidationError("JobResult result_payload must be an object")

    status = data["status"]
    if status == "complete":
        _validate_schema(data["result_payload"], JOB_RESULT_COMPLETE_PAYLOAD_SCHEMA, "JobResult result_payload")
        _validate_recommended_tasks(data["result_payload"]["recommended_tasks"])
        _validate_non_empty_string("summary", data["result_payload"]["summary"])
        if "decision_summary" in data:
            if not isinstance(data["decision_summary"], dict):
                raise ValidationError("JobResult decision_summary must be an object")
            _validate_schema(data["decision_summary"], DECISION_SUMMARY_SCHEMA, "JobResult decision_summary")
            _validate_confidence("confidence", data["decision_summary"]["confidence"])
        _validate_optional_non_empty_string("trace_run_id", data.get("trace_run_id"))
        _validate_optional_string_list("trace_refs", data.get("trace_refs"))
    elif status == "blocked":
        _validate_schema(data["result_payload"], JOB_RESULT_BLOCKED_PAYLOAD_SCHEMA, "JobResult result_payload")
        _validate_non_empty_string("reason", data["result_payload"]["reason"])
    else:
        _validate_optional_non_empty_string("error_code", data.get("error_code"))
        _validate_optional_non_empty_string("error_detail", data.get("error_detail"))
    return data


def validate_feedback(data: dict[str, Any]) -> dict[str, Any]:
    _validate_schema(data, FEEDBACK_SCHEMA, "Feedback")
    _validate_non_empty_string("feedback_id", data["feedback_id"])
    _validate_non_empty_string("job_id", data["job_id"])
    _validate_non_empty_string("app_id", data["app_id"])
    _validate_non_empty_string("project_id", data["project_id"])
    _validate_iso8601_timestamp("submitted_at", data["submitted_at"])
    _validate_optional_non_empty_string("actor_id", data.get("actor_id"))
    _validate_optional_result_status("linked_result_status", data.get("linked_result_status"))

    if not isinstance(data["feedback_payload"], dict):
        raise ValidationError("Feedback feedback_payload must be an object")
    _validate_schema(data["feedback_payload"], FEEDBACK_PAYLOAD_SCHEMA, "Feedback feedback_payload")
    _validate_string_list("done", data["feedback_payload"]["done"])
    _validate_string_list("edited", data["feedback_payload"]["edited"])
    _validate_string_list("declined", data["feedback_payload"]["declined"])
    return data


def _validate_recommended_tasks(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise ValidationError("Field 'recommended_tasks' must be a non-empty list")
    if len(value) > 3:
        raise ValidationError("Field 'recommended_tasks' must not contain more than 3 tasks")
    seen_ranks: set[int] = set()
    for index, task in enumerate(value):
        if not isinstance(task, dict):
            raise ValidationError(f"recommended_tasks item {index} must be an object")
        _validate_schema(task, TASK_SCHEMA, f"recommended_tasks item {index}")
        rank = task["rank"]
        if rank in seen_ranks:
            raise ValidationError("recommended_tasks ranks must be unique")
        seen_ranks.add(rank)
        if rank != index + 1:
            raise ValidationError("recommended_tasks ranks must be sequential starting at 1")
        _validate_non_empty_string("title", task["title"])
        _validate_non_empty_string("why_now", task["why_now"])
        _validate_non_empty_string("expected_advantage", task["expected_advantage"])
        _validate_string_list("evidence_refs", task["evidence_refs"])
        if not task["evidence_refs"]:
            raise ValidationError("recommended_tasks evidence_refs must not be empty")


def _validate_schema(data: dict[str, Any], schema: dict[str, Any], artifact_name: str) -> None:
    for field_name, field_schema in schema.items():
        if field_name not in data:
            raise ValidationError(f"{artifact_name} is missing required field '{field_name}'")
        _validate_field(field_name, data[field_name], field_schema)


def _validate_field(name: str, value: Any, schema: Any) -> None:
    if isinstance(schema, set):
        if value not in schema:
            raise ValidationError(f"Field '{name}' must be one of {sorted(schema)}")
        return
    if isinstance(schema, tuple):
        if not isinstance(value, schema):
            raise ValidationError(f"Field '{name}' must be of type {schema}")
        return
    if isinstance(schema, type):
        if not isinstance(value, schema):
            raise ValidationError(f"Field '{name}' must be of type {schema.__name__}")
        return
    raise ValidationError(f"Unsupported schema definition for field '{name}'")


def _validate_string_list(name: str, value: Any) -> None:
    if not isinstance(value, list):
        raise ValidationError(f"Field '{name}' must be a list")
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValidationError(f"Field '{name}' item {index} must be a string")


def _validate_confidence(name: str, value: Any) -> None:
    if not isinstance(value, (int, float)):
        raise ValidationError(f"Field '{name}' must be numeric")
    if value < 0 or value > 1:
        raise ValidationError(f"Field '{name}' must be between 0 and 1")


def _validate_non_empty_string(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Field '{name}' must be a non-empty string")


def _validate_optional_non_empty_string(name: str, value: Any) -> None:
    if value is None:
        return
    _validate_non_empty_string(name, value)


def _validate_optional_string_list(name: str, value: Any) -> None:
    if value is None:
        return
    _validate_string_list(name, value)


def _validate_iso8601_timestamp(name: str, value: Any) -> None:
    _validate_non_empty_string(name, value)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"Field '{name}' must be a valid ISO-8601 timestamp") from exc


def _validate_optional_iso8601_timestamp(name: str, value: Any) -> None:
    if value is None:
        return
    _validate_iso8601_timestamp(name, value)


def _validate_optional_result_status(name: str, value: Any) -> None:
    if value is None:
        return
    if value not in JOB_RESULT_SCHEMA["status"]:
        raise ValidationError(f"Field '{name}' must be one of {sorted(JOB_RESULT_SCHEMA['status'])}")
