# Agent.Chappie Roadmap

## Phase 1 - Triad refactor

Status:

- dry-run validated

Acceptance criteria:

- `StructuredTaskObject`, `ExecutionPlan`, and `DecisionRecord` are explicit and separate
- each artifact is schema-validated
- router logic is executable
- trace files are written for each run
- one complete dry-run is proven with command output

Proof requirements:

- unit tests pass
- dry-run command output shows all artifacts
- trace file paths exist on disk

## Phase 2 - Runnable local system

Status:

- implemented
- dry-run validated
- host live-run validated
- sandbox live-run restricted

Acceptance criteria:

- live-run reaches local model transport
- live-run produces triad artifacts
- live-run completes or fails with explicit trace evidence

Proof requirements:

- exact live-run command
- exact live-run output
- persisted trace files from live-run

## Phase 2.5 - Operational runtime foundation

Status:

- implemented and evidenced on host

Acceptance criteria:

- launchd plist exists
- watchdog plist exists
- heartbeat/status mechanism exists
- watchdog stale detection exists
- bounded restart policy is defined
- install/remove/status tooling exists
- crash/freeze/manual recovery runbooks exist

Proof requirements:

- plist validation output
- runtime heartbeat output
- watchdog healthy/stale output
- crash recovery output
- watchdog launchd output
- service commands documented
- launchd service state output

## Phase 2.6 - Runtime hardening

Status:

- implemented and evidenced on host

Acceptance criteria:

- supervision model is explicit
- runtime crash recovery is automatic
- watchdog recovery is persistent, not manual-only
- stale recovery is proven against the real runtime status directory
- equivalent login-session startup behavior is proven

Proof requirements:

- runtime `KeepAlive=true` service output
- watchdog launchd output
- crash recovery output with pid change
- stale recovery output on `runtime_status/`
- install/uninstall/status command output

## Phase 2.7 - Layered platform boundary

Status:

- documented and accepted

Acceptance criteria:

- Core Layer, Scheduler Layer, and App Layer are documented
- app-specific logic is explicitly excluded from the core
- a platform-boundary decision record exists
- v1 job, result, and feedback contracts exist
- per-app identity requirements are defined

Proof requirements:

- updated architecture docs
- updated roadmap
- decision record
- contract documents

## Phase 2.8 - Minimal scheduler foundation

Status:

- documented and accepted at the design level

Acceptance criteria:

- serial scheduler policy is defined
- queue state model is defined
- resource policy v1 is defined
- app and project isolation keys are defined
- one worked end-to-end example exists

Proof requirements:

- scheduler design documentation
- state model
- contract examples

## Phase 3 - First app-facing MVP contract

Status:

- documented and accepted at the contract level

Acceptance criteria:

- one domain is defined
- one user type is defined
- one recommendation loop is defined
- app submits jobs to the core through explicit contracts
- one worked MVP flow exists

Proof requirements:

- product scope document
- job, result, and feedback examples
- updated architecture docs

## Phase 3.5 - MVP contract formalization

Status:

- formalized at the schema level

Acceptance criteria:

- Job Request v1 schema is machine-validated
- Job Result v1 schema is machine-validated
- Feedback v1 schema is machine-validated
- MVP payload structures are machine-validated
- contract vocabulary is standardized across docs

Proof requirements:

- schema files
- validation examples
- updated contract docs
- validation test evidence

## Phase 4 - First app implementation

Status:

- implemented and accepted as a thin public test app

Acceptance criteria:

- thin app layer only
- app submits jobs through accepted contracts
- app receives results and captures feedback
- no orchestration or model logic is embedded in the app
- auth is explicitly deferred for the public test release
- anonymous demo identifiers are used instead of authenticated ownership

Proof requirements:

- app boundary implementation
- contract integration evidence
- feedback capture evidence

## Phase 4.5 - Auth integration

Status:

- planned, not implemented

Acceptance criteria:

- external SSO/OIDC is integrated
- authenticated ownership is added above the app boundary
- protected feedback attribution exists
- access control is enforced without changing the core contracts

Proof requirements:

- auth integration docs
- verified callback/logout flow
- protected project access evidence

## Phase 5 - Private worker bridge and continuous observation model

Status:

- partially accepted

## Phase 6l - Drafter, Writer, Judge recommendation pipeline

Status:

- in implementation

Acceptance criteria:

- every ingested source contributes to worker-drafted knowledge segments
- draft knowledge segments are persisted in the local worker brain
- writer can generate concrete business-value tasks from those segments, including missing-information tasks when evidence gaps block a stronger move
- judge adds task priority, best-before timing, and next-best-action selection
- the app surfaces draft segments, written tasks, and judged metadata without moving logic into the frontend

Proof requirements:

- persisted `draft_knowledge_segments` in the local worker store
- workspace payload evidence showing draft segments
- task output with `priority_label`, `best_before`, and `is_next_best_action`
- updated app and runbook documentation

Acceptance criteria:

- the demo bridge is replaced by a real private worker bridge path
- hidden `SystemObservation v1` signals are extracted and stored
- system observations are deduplicated and persisted in a local Mac mini database
- worker-side knowledge state is refreshed continuously
- visible task output remains bounded to ranked user-facing actions
- evidence refs in visible tasks map back to stored observations

Proof requirements:

- worker bridge code
- app API bridge code
- local observation-store schema
- local bridge verification output
- updated architecture and app runbooks
- any production bug correction in this phase family must be a root-cause fix; patch-only symptom masking is explicitly disallowed

## Phase 6 - execution observability enhancements

Status:

- planned, not implemented

Acceptance criteria:

- richer execution observability extends beyond the already completed runtime supervision baseline
- future operator tooling improves inspection without changing the core boundary model

Proof requirements:

- observability design or implementation evidence
- example operator workflows

## Phase 7 - Real task learning loop

Status:

- partially implemented
- not yet accepted as complete

What is already true:

- task cards now support live operator actions such as:
  - `Done`
  - `Adjust`
  - `Delete`
  - `Delete and teach`
  - `Hold for later`
  - `Remove source and rebuild`
- task-card feedback now saves automatically from the action itself or from text-field blur
- feedback is persisted locally in the Mac mini brain
- the checklist regenerates after feedback instead of waiting for a second manual submit step

What is still missing:

- the system does not yet behave like a strong immediate learning loop in all cases
- bad task cards are not yet replaced sharply enough after every decline/delete/comment
- comment text is not yet shaping future task wording and ranking strongly enough
- hold/delete states are stored, but their effect on future task quality is still weaker than the product goal

Plain-English objective:

When You say a task is bad, the system should immediately understand that signal, replace the task, keep the checklist at exactly 3, and stop making the same kind of mistake as often in future runs.

Required behavior:

- `decline_and_replace`
  - if You reject a task, We should generate a replacement immediately
  - the checklist should stay at exactly 3 tasks
  - the replacement should not be a trivial restatement of the rejected task

- `delete_and_teach`
  - if You delete a task and explain why, We should remove it from the live set and store that explanation as local learning
  - future similar tasks should be penalized or rewritten

- `comment_driven_regeneration`
  - if You comment that a task is vague, overlapping, weak, badly timed, or pointed at the wrong channel, that comment should influence the regenerated replacement
  - comments should matter even when You do not fully rewrite the task yourself

- `edit_as_preference_learning`
  - if You adjust a task title or wording, We should treat that as a preferred pattern
  - future similar tasks should move toward the edited form

- `always_three_after_feedback`
  - after decline, delete, hold, or comment-driven replacement, the visible checklist should still contain exactly 3 tasks unless the source itself was explicitly removed and the project must be rebuilt from weaker evidence

Acceptance criteria:

- one rejected task is replaced immediately
- one deleted-and-taught task changes later task generation
- one comment changes the regenerated output in a visible way
- one edited task creates a detectable preference pattern
- the checklist remains at 3 tasks after replacement
- learning stays local to the Mac mini brain

Proof requirements:

- updated worker tests
- one worked before/after example per feedback type
- exact local persistence paths and schema references
- explicit handoff documenting what still remains after the pass

## Phase 8 - 3steps production-credible delivery (first app)

**Product name:** 3steps (consultant follow-up web app as the first shipping surface).

Status:

- in progress (Phase 8)

Objective:

- credible **action engine**: ingest context, generate exactly **3** actions, learn from operator feedback on the **app/API path**, regenerate without degrading into disguised weak or duplicate tasks

Acceptance criteria (summary; full gates in [`docs/phase8_milestones_and_gates.md`](phase8_milestones_and_gates.md)):

- learning loop: decline/replace, delete-and-teach (semantic), comment-driven regen, bounded memory (decay/caps), **reversible** teach (inspect + delete one + undo last teach)
- **Feedback v2** documented and used end-to-end: [`docs/09_contracts/feedback_v2.md`](09_contracts/feedback_v2.md)
- every task carries honest **`task_strength`**: `strong_action` | `tactical_action` | `exploratory_action` with subtle UI
- proof via **Next.js API** (raw JSON + DB rows + before/after tasks) for `decline_and_replace`, `delete_and_teach`, comment-driven regeneration; CI runs deterministic tests; fragile live-model cases optional in CI
- reference **beta workflow** passes: one consultant, one project, real sources, full feedback cycle — sign-off: developer + architect + product owner

Architect decisions:

- [`docs/08_handoffs/handoff_20260325_phase8_3steps_architect_decisions.md`](08_handoffs/handoff_20260325_phase8_3steps_architect_decisions.md)

Non-goals:

- no auth, chat, global learning, architecture redesign, or dashboard sprawl (see milestones doc)

## Phase 7 - task engine

Status:

- planned, not implemented

Acceptance criteria:

- queued tasks move through a defined lifecycle
- task states are inspectable

Proof requirements:

- task state model
- example task transitions

## Phase 9 - skills

Status:

- planned, not implemented

Acceptance criteria:

- tool/skill loading is bounded and explicit
- governance rules remain intact

Proof requirements:

- example skill integration
- audit trail evidence

## Phase 10 - offline learning

Status:

- planned, not implemented

Acceptance criteria:

- offline adaptation path is defined
- live execution remains stable and deterministic

Proof requirements:

- documented offline learning workflow
- promotion/evaluation criteria

## Product Track A - Narrow recommendation MVP

### A1

- choose one domain only

### A2

- choose one user type only

### A3

- recommendation loop:
  user provides context or upload
  Agent.Chappie recommends tasks
  user marks done, edited, or declined
  feedback is stored
  future recommendations improve

### A4

- keep the Mac mini as a private worker behind the app boundary
