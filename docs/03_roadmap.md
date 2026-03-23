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

## Phase 7 - task engine

Status:

- planned, not implemented

Acceptance criteria:

- queued tasks move through a defined lifecycle
- task states are inspectable

Proof requirements:

- task state model
- example task transitions

## Phase 8 - skills

Status:

- planned, not implemented

Acceptance criteria:

- tool/skill loading is bounded and explicit
- governance rules remain intact

Proof requirements:

- example skill integration
- audit trail evidence

## Phase 8 - learning

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
