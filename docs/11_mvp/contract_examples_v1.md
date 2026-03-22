# MVP Contract Examples v1

## Job Request example

```json
{
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
    "artifacts": [
      {
        "type": "upload",
        "ref": "upload_meeting_notes_001"
      }
    ]
  },
  "requested_by": "consultant_001"
}
```

## Job Result example

```json
{
  "job_id": "job_mvp_0001",
  "app_id": "app_consultant_followup",
  "project_id": "client_acme_q2",
  "status": "complete",
  "completed_at": "2026-03-22T08:02:00+00:00",
  "result_payload": {
    "recommended_tasks": [
      "Send recap email to the client",
      "Draft the revised milestone plan",
      "Confirm ownership for the open action items"
    ],
    "summary": "The uploaded meeting notes indicate several unresolved client follow-up tasks."
  },
  "decision_summary": {
    "route": "proceed",
    "confidence": 0.86
  },
  "trace_run_id": "20260322T080200Z_mvp00001",
  "trace_refs": [
    "01_request.json",
    "05_outcome.json"
  ]
}
```

## Feedback example

```json
{
  "feedback_id": "feedback_mvp_0001",
  "job_id": "job_mvp_0001",
  "app_id": "app_consultant_followup",
  "project_id": "client_acme_q2",
  "feedback_type": "task_response",
  "submitted_at": "2026-03-22T08:10:00+00:00",
  "user_action": "edited",
  "feedback_payload": {
    "done": [
      "Send recap email to the client"
    ],
    "edited": [
      "Draft the revised milestone plan with updated target dates"
    ],
    "declined": [
      "Confirm ownership for the open action items"
    ]
  },
  "actor_id": "consultant_001",
  "linked_result_status": "complete"
}
```

## Capability language check

- uses `requested_capability`
- avoids page or UI names
- keeps the core agnostic to app page structure
