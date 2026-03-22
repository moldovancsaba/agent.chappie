# Contract: Job Request v1

## Purpose

Defines the app-to-platform request envelope for future app-layer clients.

## Ownership

- produced by the App Layer
- accepted by the Scheduler Layer
- executed by the Core Layer after scheduling

## Required fields

- `job_id`
- `app_id`
- `project_id`
- `priority_class`
- `job_class`
- `submitted_at`
- `requested_capability`
- `input_payload`

## Recommended fields

- `requested_by`
- `deadline_at`
- `source_refs`
- `trace_parent_id`
- `policy_tags`

## Example shape

```json
{
  "job_id": "job_0001",
  "app_id": "app_tasks",
  "project_id": "project_alpha",
  "priority_class": "normal",
  "job_class": "heavy",
  "submitted_at": "2026-03-22T07:00:00+00:00",
  "requested_capability": "task_recommendation",
  "input_payload": {
    "prompt": "Review uploaded context and recommend next tasks.",
    "artifacts": [
      {
        "type": "upload",
        "ref": "upload_123"
      }
    ]
  },
  "requested_by": "user_42",
  "policy_tags": [
    "local-first"
  ]
}
```

## Field notes

- `job_id`: unique identifier for a single submitted job
- `app_id`: stable identifier for the submitting app
- `project_id`: stable identifier for the app-specific project or workspace
- `priority_class`: scheduler priority hint such as `critical`, `normal`, or `low`
- `job_class`: scheduler capacity hint such as `heavy` or `light`
- `requested_capability`: app-agnostic capability name, not a UI action label
- `input_payload`: opaque structured input owned by the app contract

## Boundary rule

The job request defines intent and input only. It does not define how the core should route, schedule, or prompt the model.

## Formal schema references

- schema definitions: `src/agent_chappie/contract_schemas.py`
- validation entrypoint: `agent_chappie.validation.validate_job_request`
