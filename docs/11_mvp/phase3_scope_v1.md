# Phase 3 Scope v1

## Domain

Client project follow-up task recommendation.

## User type

Independent consultant managing one client project.

## Decision-support problem

The user uploads project context such as meeting notes, call summaries, or working documents and needs a short, prioritized list of recommended follow-up tasks for the client project.

## Input the app submits

- uploaded project context
- optional user prompt or emphasis
- stable `app_id` and `project_id`
- one capability-oriented job request

## Output the app receives

- recommended follow-up tasks
- supporting rationale or summary
- trace-linked job result metadata

## Feedback capture

The user responds to recommended tasks by marking them:

- done
- edited
- declined

The feedback returns through the accepted feedback contract and stays above the core boundary.

## Recommendation loop

1. user provides project context
2. app submits one capability-oriented job request
3. scheduler interprets and orders the job
4. core executes the job
5. app receives recommended follow-up tasks
6. user submits feedback on the recommendations

## Scope guard

- one domain only
- one user type only
- one recommendation loop only
- no app implementation in this phase
- no scheduler implementation in this phase
