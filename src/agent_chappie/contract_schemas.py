from __future__ import annotations

JOB_PRIORITY_CLASS = {"critical", "normal", "low"}
JOB_CLASS = {"heavy", "light"}
JOB_RESULT_STATUS = {"complete", "failed", "blocked"}
FEEDBACK_ACTION = {"done", "edited", "declined", "commented", "deleted_silent", "deleted_with_annotation", "held_for_later"}
FEEDBACK_TYPE = {"task_response"}
CONTEXT_TYPE = {"meeting_notes", "call_summary", "working_document"}
ARTIFACT_TYPE = {"upload"}
DECISION_ROUTE = {"proceed", "revise", "stop"}
BUSINESS_IMPACT = {"low", "medium", "high"}
SIGNAL_TYPE = {
    "pricing_change",
    "opening",
    "closure",
    "staffing",
    "offer",
    "asset_sale",
    "messaging_shift",
    "proof_signal",
    "vendor_adoption",
}


JOB_REQUEST_SCHEMA = {
    "job_id": str,
    "app_id": str,
    "project_id": str,
    "priority_class": JOB_PRIORITY_CLASS,
    "job_class": JOB_CLASS,
    "submitted_at": str,
    "requested_capability": str,
    "input_payload": dict,
}


JOB_REQUEST_INPUT_PAYLOAD_SCHEMA = {
    "context_type": CONTEXT_TYPE,
    "prompt": str,
    "artifacts": list,
}


JOB_REQUEST_ARTIFACT_SCHEMA = {
    "type": ARTIFACT_TYPE,
    "ref": str,
}


SYSTEM_OBSERVATION_SCHEMA = {
    "signal_id": str,
    "signal_type": SIGNAL_TYPE,
    "competitor": str,
    "region": str,
    "summary": str,
    "source_ref": str,
    "observed_at": str,
    "confidence": (int, float),
    "business_impact": BUSINESS_IMPACT,
}


TASK_SCHEMA = {
    "rank": int,
    "title": str,
    "why_now": str,
    "expected_advantage": str,
    "evidence_refs": list,
}


JOB_RESULT_SCHEMA = {
    "job_id": str,
    "app_id": str,
    "project_id": str,
    "status": JOB_RESULT_STATUS,
    "completed_at": str,
    "result_payload": dict,
}


DECISION_SUMMARY_SCHEMA = {
    "route": DECISION_ROUTE,
    "confidence": (int, float),
}


JOB_RESULT_COMPLETE_PAYLOAD_SCHEMA = {
    "recommended_tasks": list,
    "summary": str,
}


JOB_RESULT_BLOCKED_PAYLOAD_SCHEMA = {
    "reason": str,
}


FEEDBACK_SCHEMA = {
    "feedback_id": str,
    "job_id": str,
    "app_id": str,
    "project_id": str,
    "feedback_type": FEEDBACK_TYPE,
    "submitted_at": str,
    "user_action": FEEDBACK_ACTION,
    "feedback_payload": dict,
}


FEEDBACK_PAYLOAD_SCHEMA = {
    "done": list,
    "edited": list,
    "declined": list,
    "commented": list,
    "deleted_silent": list,
    "deleted_with_annotation": list,
    "held_for_later": list,
}
