#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.validation import ValidationError, validate_feedback, validate_job_request, validate_job_result


VALID_JOB_REQUEST = {
    "job_id": "job_mvp_0001",
    "app_id": "app_consultant_followup",
    "project_id": "client_acme_q2",
    "priority_class": "normal",
    "job_class": "heavy",
    "submitted_at": "2026-03-22T08:00:00+00:00",
    "requested_capability": "followup_task_recommendation",
    "input_payload": {
        "context_type": "meeting_notes",
        "prompt": "Recommend the next follow-up tasks for this client project.",
        "artifacts": [{"type": "upload", "ref": "upload_meeting_notes_001"}],
    },
    "requested_by": "consultant_001",
}

VALID_JOB_RESULT = {
    "job_id": "job_mvp_0001",
    "app_id": "app_consultant_followup",
    "project_id": "client_acme_q2",
    "status": "complete",
    "completed_at": "2026-03-22T08:02:00+00:00",
    "result_payload": {
        "recommended_tasks": [
            "Send recap email to the client",
            "Draft the revised milestone plan",
            "Confirm ownership for the open action items",
        ],
        "summary": "The uploaded meeting notes indicate several unresolved client follow-up tasks.",
    },
    "decision_summary": {"route": "proceed", "confidence": 0.86},
    "trace_run_id": "20260322T080200Z_mvp00001",
    "trace_refs": ["01_request.json", "05_outcome.json"],
}

VALID_FEEDBACK = {
    "feedback_id": "feedback_mvp_0001",
    "job_id": "job_mvp_0001",
    "app_id": "app_consultant_followup",
    "project_id": "client_acme_q2",
    "feedback_type": "task_response",
    "submitted_at": "2026-03-22T08:10:00+00:00",
    "user_action": "edited",
    "feedback_payload": {
        "done": ["Send recap email to the client"],
        "edited": ["Draft the revised milestone plan with updated target dates"],
        "declined": ["Confirm ownership for the open action items"],
    },
    "actor_id": "consultant_001",
    "linked_result_status": "complete",
}

INVALID_FEEDBACK = {
    "feedback_id": "feedback_bad_0001",
    "job_id": "job_mvp_0001",
    "app_id": "app_consultant_followup",
    "project_id": "client_acme_q2",
    "feedback_type": "task_response",
    "submitted_at": "2026-03-22T08:10:00+00:00",
    "user_action": "edited",
    "feedback_payload": {
        "accepted": ["Send recap email to the client"],
        "edited": [],
        "declined": [],
    },
}


def main() -> int:
    valid_examples = {
        "job_request": validate_job_request(VALID_JOB_REQUEST),
        "job_result": validate_job_result(VALID_JOB_RESULT),
        "feedback": validate_feedback(VALID_FEEDBACK),
    }

    print(json.dumps({"valid_examples": valid_examples}, indent=2, sort_keys=True))
    try:
        validate_feedback(INVALID_FEEDBACK)
    except ValidationError as exc:
        print(json.dumps({"invalid_example": "feedback", "validation_error": str(exc)}, indent=2, sort_keys=True))
        return 0

    print(json.dumps({"invalid_example": "feedback", "validation_error": "expected a failure but validation passed"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
