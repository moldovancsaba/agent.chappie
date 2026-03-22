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
      "Review source upload",
      "Draft next action list"
    ]
  },
  "decision_summary": {
    "route": "proceed",
    "confidence": 0.85
  },
  "trace_run_id": "20260322T070200Z_abc12345",
  "trace_refs": [
    "01_request.json",
    "05_outcome.json"
  ]
}
```

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
