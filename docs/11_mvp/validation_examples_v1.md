# MVP Validation Examples v1

## Purpose

Shows how the formal schema layer validates accepted MVP contracts.

## Valid Job Request example

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

## Valid Job Result example

```json
{
  "job_id": "job_mvp_0001",
  "app_id": "app_consultant_followup",
  "project_id": "client_acme_q2",
  "status": "complete",
  "completed_at": "2026-03-22T08:02:00+00:00",
  "result_payload": {
    "recommended_tasks": [
      {
        "rank": 1,
        "title": "Publish a 7-day comparison offer and update the pricing page against FlowOps's latest fee change",
        "why_now": "FlowOps raised pricing this week and the move is likely to affect parent comparison shopping before the next intake cycle.",
        "expected_advantage": "Protects enrollment and improves intake conversion before the next sign-up cycle.",
        "evidence_refs": [
          "sig_price_001"
        ]
      },
      {
        "rank": 2,
        "title": "Contact FlowOps's owner this week about acquiring released customers, staff, or equipment",
        "why_now": "FlowOps is showing a closure signal this week and the asset window is time-sensitive.",
        "expected_advantage": "Increases player capacity, local revenue, or facility access faster than organic growth.",
        "evidence_refs": [
          "sig_close_001"
        ]
      },
      {
        "rank": 3,
        "title": "Request the asset list and place a bid on discounted equipment before the sell-off closes",
        "why_now": "An asset-sale signal was detected in the region this week.",
        "expected_advantage": "Reduces equipment cost this month and protects operating margin for coaching or promotion.",
        "evidence_refs": [
          "sig_sale_001"
        ]
      }
    ],
    "summary": "Three competitive actions were prioritized from current source input and stored market observations."
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

## Valid Feedback example

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

## Invalid Feedback example

```json
{
  "feedback_id": "feedback_bad_0001",
  "job_id": "job_mvp_0001",
  "app_id": "app_consultant_followup",
  "project_id": "client_acme_q2",
  "feedback_type": "task_response",
  "submitted_at": "2026-03-22T08:10:00+00:00",
  "user_action": "edited",
  "feedback_payload": {
    "accepted": [
      "Send recap email to the client"
    ],
    "edited": [],
    "declined": []
  }
}
```

Expected validation failure reason:

- `Feedback feedback_payload is missing required field 'done'`
