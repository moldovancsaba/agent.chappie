# Contract: Job Result v1

## Purpose

Defines the platform-to-app result envelope returned after a job completes or fails.

## Ownership

- produced by the Core Layer after execution
- returned through the Scheduler Layer
- consumed by the App Layer

## Required fields

- `job_id`
- `app_id`
- `project_id`
- `status`
- `completed_at`
- `result_payload`

## Recommended fields

- `decision_summary`
- `trace_run_id`
- `trace_refs`
- `error_code`
- `error_detail`

## Example shape

```json
{
  "job_id": "job_0001",
  "app_id": "app_tasks",
  "project_id": "project_alpha",
  "status": "complete",
  "completed_at": "2026-03-22T07:02:00+00:00",
  "result_payload": {
    "recommended_tasks": [
      {
        "rank": 1,
        "title": "Publish a 7-day comparison offer and update the pricing page against FlowOps's latest fee change",
        "why_now": "FlowOps changed pricing this week and the move is likely to affect parent comparison shopping before the next intake cycle.",
        "expected_advantage": "Protects enrollment and improves intake conversion before the next sign-up cycle.",
        "evidence_refs": [
          "sig_0775a2c2f78d"
        ]
      },
      {
        "rank": 2,
        "title": "Contact FlowOps's owner this week about acquiring released customers, staff, or equipment",
        "why_now": "FlowOps is showing a closure or distress signal and the asset window is time-sensitive.",
        "expected_advantage": "Increases player capacity, local revenue, or facility access faster than organic growth.",
        "evidence_refs": [
          "sig_fdd325070fac"
        ]
      },
      {
        "rank": 3,
        "title": "Request the asset list and place a bid on discounted equipment before the sell-off closes",
        "why_now": "An asset-sale signal was detected in the current region this week.",
        "expected_advantage": "Reduces equipment cost this month and protects operating margin for coaching or promotion.",
        "evidence_refs": [
          "sig_08cfdd451f33"
        ]
      }
    ],
    "summary": "Three competitive actions were prioritized from current source input and stored market observations."
  },
  "decision_summary": {
    "route": "proceed",
    "confidence": 0.82
  },
  "trace_run_id": "worker-job_0001",
  "trace_refs": [
    "sig_0775a2c2f78d",
    "sig_fdd325070fac",
    "sig_08cfdd451f33"
  ]
}
```

## Ranked task rules

For the current MVP capability:

- return exactly 3 tasks when strong evidence exists
- rank values must be `1`, `2`, `3`
- every task must be executable within 7 days
- every task title must describe a concrete action, not generic strategy wording
- `evidence_refs` must map to stored signal identifiers or source refs
- user-visible output must not expose the full internal observation list
- each recommended task should include **`task_strength`**: `strong_action` | `tactical_action` | `exploratory_action` (Phase 8 / 3steps) so exploratory moves are not disguised as strong actions; see [`feedback_v2.md`](feedback_v2.md)

If strong evidence is insufficient, the result may return a blocked or no-strong-action response instead of hallucinated tasks.

## Allowed statuses

- `complete`
- `failed`
- `blocked`

`queued` and `running` remain scheduler states, not final result-envelope statuses.

## Formal schema references

- schema definitions: `src/agent_chappie/contract_schemas.py`
- validation entrypoint: `agent_chappie.validation.validate_job_result`

## Boundary rule

The result contract returns structured outcome data and trace linkage. It does not expose internal prompting strategy or allow the app to bypass the scheduler or runtime policies.
