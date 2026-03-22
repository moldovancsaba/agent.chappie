# Contract: Feedback v1

## Purpose

Defines the app-to-platform feedback envelope for future improvement loops without embedding app logic in the core.

## Ownership

- produced by the App Layer
- stored above the core boundary
- may later inform offline evaluation or recommendation improvement

## Required fields

- `feedback_id`
- `job_id`
- `app_id`
- `project_id`
- `feedback_type`
- `submitted_at`

## Recommended fields

- `user_action`
- `feedback_payload`
- `actor_id`
- `linked_result_status`

## Example shape

```json
{
  "feedback_id": "feedback_0001",
  "job_id": "job_0001",
  "app_id": "app_tasks",
  "project_id": "project_alpha",
  "feedback_type": "task_response",
  "submitted_at": "2026-03-22T07:05:00+00:00",
  "user_action": "edited",
  "feedback_payload": {
    "done": [
      "Review source upload"
    ],
    "edited": [
      "Draft an owner-specific task list"
    ],
    "declined": []
  },
  "actor_id": "user_42",
  "linked_result_status": "complete"
}
```

## Allowed user actions

- `done`
- `edited`
- `declined`

## Formal schema references

- schema definitions: `src/agent_chappie/contract_schemas.py`
- validation entrypoint: `agent_chappie.validation.validate_feedback`

## Boundary rule

Feedback is a contract input to the platform boundary. It does not directly mutate core routing policy or runtime configuration.
