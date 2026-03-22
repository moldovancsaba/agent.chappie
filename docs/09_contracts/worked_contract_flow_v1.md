# Worked Contract Flow v1

## Purpose

Provides one synthetic end-to-end example showing how the app, scheduler, and core boundary interact without implementing scheduler code.

## Identity carried through the whole flow

- `app_id`: `app_tasks`
- `project_id`: `project_alpha`

## Step 1: Job Request v1

```json
{
  "job_id": "job_0001",
  "app_id": "app_tasks",
  "project_id": "project_alpha",
  "priority_class": "normal",
  "job_class": "heavy",
  "submitted_at": "2026-03-22T07:30:00+00:00",
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
  "requested_by": "user_42"
}
```

## Step 2: Scheduler interpretation

- the scheduler accepts the request because required identity and capability fields are present
- the job enters `queued`
- the scheduler identifies this as a `heavy` job
- under v1 rules, it must wait until no other heavy job is running
- when capacity opens, it moves to `running`

## Step 3: State transition path

```text
queued -> running -> complete
```

### `queued`

- job accepted
- waiting for heavy-job capacity

### `running`

- scheduler selects the job
- core executes the governed triad flow

### `complete`

- core returns a successful result envelope
- scheduler marks the job complete and returns the result to the app

## Step 4: Job Result v1

```json
{
  "job_id": "job_0001",
  "app_id": "app_tasks",
  "project_id": "project_alpha",
  "status": "complete",
  "completed_at": "2026-03-22T07:32:00+00:00",
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
  "trace_run_id": "20260322T073200Z_abc12345",
  "trace_refs": [
    "01_request.json",
    "05_outcome.json"
  ]
}
```

## Step 5: Feedback v1

```json
{
  "feedback_id": "feedback_0001",
  "job_id": "job_0001",
  "app_id": "app_tasks",
  "project_id": "project_alpha",
  "feedback_type": "task_response",
  "submitted_at": "2026-03-22T07:35:00+00:00",
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

## Boundary check

- the app submits a job and later feedback
- the scheduler owns state and ordering
- the core owns execution
- the same `app_id` and `project_id` remain stable across request, result, and feedback
