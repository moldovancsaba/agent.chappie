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
        "title": "Adjust academy pricing and offer positioning against FlowOps",
        "why_now": "Pricing movement was detected for FlowOps and is likely to affect parent comparison shopping.",
        "expected_advantage": "Protects enrollment and reduces switching risk caused by competitor price pressure.",
        "evidence_refs": [
          "sig_0775a2c2f78d"
        ]
      },
      {
        "rank": 2,
        "title": "Investigate whether FlowOps is available for acquisition or player transfer capture",
        "why_now": "Closure or distress signals were detected for FlowOps.",
        "expected_advantage": "Creates a faster path to growth through acquisition, player capture, or facility access.",
        "evidence_refs": [
          "sig_fdd325070fac"
        ]
      },
      {
        "rank": 3,
        "title": "Check for discounted equipment or infrastructure purchase opportunities",
        "why_now": "An asset-sale signal was detected in the current region.",
        "expected_advantage": "Improves margin and frees budget for coaching quality or promotion.",
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
- `evidence_refs` must map to stored signal identifiers or source refs
- user-visible output must not expose the full internal observation list

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
