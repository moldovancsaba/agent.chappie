# Scheduler Foundation v1

## Purpose

Defines the minimal scheduler foundation needed to preserve clean multi-app architecture before any scheduler code is implemented.

## Responsibilities

- accept jobs from app-layer clients through the job request contract
- maintain queue state for submitted jobs
- apply priority ordering rules
- apply capacity and concurrency rules
- preserve isolation by `app_id` and `project_id`
- hand eligible work to the core layer for execution

## Non-goals

- no scheduler implementation in code yet
- no quota engine
- no cooldown engine
- no fairness algorithm beyond bounded v1 ordering rules
- no UI logic
- no app-specific workflow logic
- no model prompting ownership

## Relation to the Core Layer

- the scheduler decides when work is eligible to run
- the core decides how eligible work is executed through the governed triad
- the scheduler does not mutate triad schemas, router logic, or runtime supervision behavior

## Relation to the App Layer

- apps submit `Job Request v1`
- apps receive status and `Job Result v1`
- apps submit `Feedback v1`
- apps do not decide execution order or concurrency

## Scheduler state model

### `queued`

Meaning:

- the job has been accepted by the scheduler but has not started execution

Entry conditions:

- a valid `Job Request v1` is accepted
- required identity fields are present
- the job is waiting for capacity or higher-priority work to clear

Exit conditions:

- move to `running` when capacity and ordering rules allow execution
- move to `blocked` if a dependency or policy rule prevents execution

### `running`

Meaning:

- the job has been selected by the scheduler and handed to the core for execution

Entry conditions:

- the job was previously `queued`
- no higher-priority eligible job preempts it under v1 rules
- capacity rules allow execution

Exit conditions:

- move to `complete` when execution finishes successfully
- move to `failed` when execution ends with an error
- move to `blocked` if execution is paused by a policy or dependency gate

### `complete`

Meaning:

- the job finished successfully and a result contract is available

Entry conditions:

- the job was `running`
- the core produced a successful result

Exit conditions:

- terminal state in v1

### `failed`

Meaning:

- the job ended unsuccessfully and requires retry or review

Entry conditions:

- the job was `running`
- execution produced an unrecoverable error outcome for the current attempt

Exit conditions:

- terminal state in v1

### `blocked`

Meaning:

- the job cannot proceed until a non-capacity condition is resolved

Entry conditions:

- a policy gate prevents execution
- a dependency is missing
- external approval or required input is missing

Exit conditions:

- move to `queued` when the blocking condition clears
- remain `blocked` while the blocking condition persists

## Serial dispatch rules v1

- serial execution by default
- one heavy job at a time
- no app bypasses scheduler ordering
- higher `priority_class` jobs are considered before lower-priority eligible jobs
- bounded concurrency remains conservative in v1

## Capacity policy v1

### Job classes

- `heavy`: jobs expected to consume substantial model/runtime capacity
- `light`: jobs expected to consume limited capacity

### Allowed concurrently in v1

- one `heavy` job and no other `heavy` job
- no general concurrent execution guarantee for `light` jobs yet

### Explicitly disallowed in v1

- concurrent heavy-job execution
- app-specific exceptions to capacity policy
- unconstrained parallel dispatch

## App and project isolation rules

- `app_id` identifies the app client namespace
- `project_id` identifies the stable project, workspace, or case inside that app
- scheduler ordering and state tracking must preserve both fields
- retries must keep the same `job_id`, `app_id`, and `project_id` lineage where appropriate
- follow-up feedback must carry the same `app_id` and `project_id` lineage as the original job
- isolation prevents one app or project from contaminating another app's work or state interpretation
