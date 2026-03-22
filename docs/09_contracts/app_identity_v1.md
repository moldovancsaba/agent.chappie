# Contract: App And Project Identity v1

## Purpose

Defines the minimum identity fields that all future jobs must carry so the scheduler can isolate work by app and project.

## Required identity fields

- `app_id`
- `project_id`
- `priority_class`
- `job_class`

## Definitions

- `app_id`: stable identifier for the app client submitting work
- `project_id`: stable identifier for the tenant, workspace, project, or case within that app
- `priority_class`: scheduler hint used for ordering policy
- `job_class`: scheduler hint used for capacity policy

## Example values

- `app_id`: `app_tasks`
- `project_id`: `project_alpha`
- `priority_class`: `critical`, `normal`, `low`
- `job_class`: `heavy`, `light`

## Identity rules

- all jobs from an app must include the same `app_id` namespace
- `project_id` must be stable across retries and follow-up feedback
- `priority_class` is a scheduling hint, not a guarantee
- `job_class` is a capacity hint, not a UI label

## Boundary rule

Identity exists to keep scheduling and isolation app-safe. It must not encode frontend implementation details or domain presentation logic.
