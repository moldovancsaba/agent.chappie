# Agent.Chappie Architecture

## Control plane

The current control plane is:

`request -> StructuredTaskObject -> ExecutionPlan -> DecisionRecord -> confidence router -> outcome`

## First-class artifacts

### StructuredTaskObject

Purpose:

- normalize the request
- define task intent and constraints
- identify candidate tools and domains
- expose draft confidence

Implementation:

- schema definition in `src/agent_chappie/schemas.py`
- validation in `src/agent_chappie/validation.py`
- produced through the model adapter `draft()` method

### ExecutionPlan

Purpose:

- describe bounded stages for execution
- define dependencies, evidence, and acceptance tests
- expose writer confidence

Implementation:

- schema definition in `src/agent_chappie/schemas.py`
- validation in `src/agent_chappie/validation.py`
- produced through the model adapter `write()` method

### DecisionRecord

Purpose:

- score feasibility and confidence
- record risk flags and rationale
- express the next routing action

Implementation:

- schema definition in `src/agent_chappie/schemas.py`
- validation in `src/agent_chappie/validation.py`
- produced through the model adapter `judge()` method

## Router

The router is explicit code, not prose.

Current routes:

- `proceed`
- `revise`
- `stop`

Current thresholds:

- `proceed` at confidence `>= 0.85`
- `revise` at confidence `>= 0.45` and `< 0.85`
- `stop` below `0.45`, on explicit stop, or if human review is required

Implementation:

- `src/agent_chappie/router.py`

## Trace persistence

Each run creates a unique trace directory and writes immutable JSON files in a stable order:

1. `01_request.json`
2. `02_structured_task_object.json`
3. `03_execution_plan.json`
4. `04_decision_record.json`
5. `05_outcome.json`

Implementation:

- `src/agent_chappie/traces.py`

If live execution fails before the triad artifacts are produced, placeholder trace files are still written so the failure path remains inspectable.

## Control-plane vs runtime separation

Control-plane responsibilities:

- artifact creation
- validation
- routing
- trace persistence

Runtime responsibilities:

- model transport through Ollama
- tool execution

Current runtime status:

- dry-run uses `DryRunModelAdapter`
- live-run uses `OllamaModelAdapter`
- live-run is validated on the host with `AGENT_MODEL=llama3:latest`
- sandbox loopback restrictions still prevent equivalent validation inside the restricted environment

## Runtime foundation

The current runtime foundation adds:

- `scripts/agent_runtime.py` for a long-lived heartbeat loop
- `src/agent_chappie/runtime.py` for heartbeat and watchdog state persistence
- `scripts/watchdog_agent.py` for stale heartbeat detection and bounded restart logic
- `ops/com.agentchappie.runtime.plist` as the launchd runtime service definition
- `ops/com.agentchappie.watchdog.plist` as the persistent watchdog schedule

This runtime layer does not change the triad flow. It adds observability and restart controls around it.

## Supervision model

The current supervision split is:

- `launchd` with `KeepAlive=true` for runtime crash and unexpected exit recovery
- a separate watchdog launchd job for stale heartbeat recovery
- bounded watchdog restart budget for restart storm protection

## Product boundary direction

Planned production boundary:

`Vercel app/API -> durable database/job layer -> Agent.Chappie private worker on the Mac mini`

This means:

- the Mac mini remains a private worker
- the public website should not depend on direct public exposure of the Mac mini
- the governed triad remains the worker-side decision core

## Layered platform boundary

Agent.Chappie is now documented as three layers with explicit boundaries.

### Core Layer

Responsibilities:

- governed triad flow
- `StructuredTaskObject`, `ExecutionPlan`, and `DecisionRecord`
- routing and policy enforcement
- trace persistence
- runtime supervision and recovery
- execution policy
- app-agnostic execution behavior

Must not contain:

- app-specific page flows
- frontend state assumptions
- branding or UI behavior
- domain-specific presentation logic
- product-specific recommendation wording

### Scheduler Layer

Responsibilities:

- job intake from future app clients
- queue state tracking
- priority handling
- capacity-aware dispatch
- bounded concurrency rules
- per-app and per-project isolation keys

Current status:

- documented only
- not implemented in code yet

Relation to the Core Layer:

- the scheduler submits ordered work to the core
- the scheduler does not change triad internals
- the scheduler does not own trace semantics or runtime supervision

Relation to the App Layer:

- the scheduler accepts app-submitted jobs through contracts
- the scheduler returns status and completion information to apps through contracts
- apps cannot bypass scheduler ordering or capacity rules

### App Layer

Responsibilities:

- gather user input
- submit jobs to Agent.Chappie through contracts
- receive structured results
- submit feedback
- remain independently deployable

Rules:

- apps do not call model runtimes directly
- apps do not embed triad orchestration
- apps do not own scheduling policy
- apps interact with Agent.Chappie through job, result, and feedback contracts only

## Boundary contracts

The platform boundary is defined by v1 document contracts:

- `docs/09_contracts/job_request_v1.md`
- `docs/09_contracts/job_result_v1.md`
- `docs/09_contracts/feedback_v1.md`
- `docs/09_contracts/app_identity_v1.md`
- `docs/09_contracts/scheduler_policy_v1.md`

These contracts prepare future app integrations without adding scheduler or app implementation to the core at this phase.

## Formal schema references

The accepted contract layer is now formalized in machine-validated Python schema definitions:

- `src/agent_chappie/contract_schemas.py`
- `src/agent_chappie/validation.py`

These schema definitions standardize:

- required fields
- allowed enums
- identity fields
- MVP payload shapes
- validation failure behavior

Phase 5 extends the formal schema layer with:

- `SystemObservation v1`
- strict ranked-task result validation
- evidence linkage from visible tasks back to hidden observation identifiers

## Scheduler design references

- `docs/10_scheduler/foundation_v1.md`
- `docs/09_contracts/worked_contract_flow_v1.md`

## Phase 3 MVP contract scope

The first app-facing MVP is defined at the contract layer only.

Current scope:

- one domain: client project follow-up task recommendation
- one user type: independent consultant managing one client project
- one recommendation loop: upload project context, receive recommended follow-up tasks, submit feedback on the recommended tasks

Implementation status:

- product scope and examples documented
- formal schemas documented and implemented
- scheduler implementation deferred
- app implementation deferred
- core remains app-agnostic

## Phase 5 private worker bridge

Phase 5 introduces the first real private worker bridge:

`Vercel app -> app API -> private Mac mini worker -> Neon-backed observations -> Job Result`

### Hidden System Observation layer

Purpose:

- continuously ingest raw market or competitor context
- normalize signals into `SystemObservation v1`
- deduplicate recent overlapping signals
- persist signals in Neon
- update lightweight project knowledge state on the worker

This layer is internal only. It must not be rendered directly in the app UI.

Authoritative storage:

- local SQLite database on the Mac mini worker

May be mirrored or summarized elsewhere only if explicitly treated as non-authoritative.

### Visible user-facing task layer

Purpose:

- convert the strongest stored signals into user-facing actions
- return exactly 3 ranked tasks when enough strong evidence exists
- keep recommendations action-oriented instead of research-oriented

Each visible task includes:

- `rank`
- `title`
- `why_now`
- `expected_advantage`
- `evidence_refs`

### Worker bridge boundary

Current worker interface:

- `POST /jobs`
- `GET /health`

Current protection:

- shared-secret header via `x-agent-shared-secret`

Current behavior:

- app submits a `Job Request v1`
- worker enriches the request with observations stored in the local Mac mini database
- worker returns a validated `Job Result v1`
- observation details remain internal and are not exposed directly to the app

## Phase 4 public test app

The first implementation-bearing app phase is intentionally public and unauthenticated.

App-layer rules for Phase 4:

- no login
- no OIDC or OAuth wiring
- no JWT verification path
- use anonymous demo identifiers instead of real user accounts
- use demo-safe content only

This keeps the app thin while preserving the accepted core, scheduler, and contract boundaries.
