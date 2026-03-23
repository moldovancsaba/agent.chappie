# Consultant Follow-Up Web App

## Purpose

This is the first thin app layer for Agent.Chappie. It exists to exercise the accepted contract layer in a public test MVP without adding auth, scheduler implementation, or core orchestration into the app.

## What the app does

- accepts one raw competitive context input
- accepts a pasted URL, raw text block, or extracted file text as raw source material
- submits one `Job Request v1`
- retrieves one `Job Result v1`
- submits one `Feedback v1`
- presents the product as a single decision surface, not a dashboard

The frontend does not own or generate the general project context. That context is inferred, enriched, and maintained on the Mac mini worker.

## Developer correction rule

Developer work on this app must deliver root-cause fixes only.

- patching around a symptom instead of fixing the underlying failure is prohibited
- if the visible UI state and the claimed system state diverge, the implementation must trace and fix the true data, state, rendering, or recovery fault
- temporary UI copy or masking changes are not acceptable as substitutes for restoring correct system behavior
- every correction pass must state the actual failure mode and the root-cause fix that resolved it

## Surface structure

The app now uses three sections only:

- `Your Checklist` as the default view with exactly 3 ranked task cards
- `Know More` as the structured knowledge surface behind the checklist
- `Sources & Jobs` as the operator-side ingestion and recurring-job surface
- a guided first-run input module that teaches the user exactly what to submit without sample business data

The main checklist view must:

- show cards, not tables
- show exactly 3 visible task cards
- expose decision actions as `Done`, `Adjust`, and `Reject`
- include a confidence indicator for the current ranked output
- replace abstract empty states with guided input options and real ingestion status
- open task detail per card instead of using `Know More` as the generic task-explanation panel

## What the app does not do

- no login
- no OIDC or SSO integration in Phase 4
- no direct model calls
- no scheduler logic
- no public exposure of the Mac mini core
- no direct UI for internal observations

## Identity model for the public test

- `app_id` stays fixed as `app_consultant_followup`
- `project_id` is generated or assigned through the worker-backed flow
- `requested_by` uses an anonymous session form such as `anonymous:<session_id>`
- feedback is demo-only and non-authoritative

## Storage modes

### Memory mode

- used by default for local bring-up
- does not require Neon
- intended for demo and development only

### Neon mode

- enabled by setting `DEMO_STORAGE_MODE=neon`
- requires `DATABASE_URL`
- uses the schema in `apps/consultant-followup-web/db/migrations/001_public_test_mvp.sql`

## Worker boundary

Phase 5 upgrades the app to support the first real private worker bridge while keeping the worker private:

`Vercel app -> durable data layer -> private worker on the Mac mini`

The app-side bridge entrypoint is:

- `POST /api/jobs`
- `GET /api/projects/[projectId]/workspace`
- `POST /api/projects/[projectId]/sources`
- `PATCH /api/projects/[projectId]/sources/[sourceId]`
- `DELETE /api/projects/[projectId]/sources/[sourceId]`
- `POST /api/projects/[projectId]/jobs`
- `PATCH /api/projects/[projectId]/jobs/[jobId]`
- `DELETE /api/projects/[projectId]/jobs/[jobId]`

The worker remains protected by a shared-secret header and returns only user-facing ranked tasks.
The app sends only raw source material and job identity. It does not send competitor, region, or project-summary fields.

Shared state can still live in Neon for the app layer, but internal intelligence state remains local to the Mac mini worker.

## Observation model

The app now depends on a two-layer intelligence model:

- hidden `SystemObservation v1` signals persisted on the worker side
- visible ranked `recommended_tasks` returned to the app
- persisted `draft_knowledge_segments` created by the drafter before the writer and judge finalize tasks

The app must not expose the internal observation layer directly.
The app must not collect or fabricate general project metadata that belongs in the worker brain.

The real decision pipeline is now:

- `Drafter`: read the full source set, normalize it, and persist editable draft knowledge segments
- `Writer`: turn those segments plus source-linked evidence into concrete business-value tasks, including missing-information tasks when evidence gaps block a stronger move
- `Judge`: rank the tasks, add priority and best-before timing, and mark the next best action

## Ingestion behavior

- URL-only submissions are fetched and normalized on the Mac mini worker before signal extraction
- raw text submissions are stored as local source snapshots before signal extraction
- file submissions are sent as real uploads and extracted on the Mac mini worker
- the app accepts one real source per submission: URL, pasted text, or one supported document
- supported document uploads are currently `.txt`, `.md`, `.csv`, `.pdf`, and `.docx`
- if the worker cannot derive three distinct, high-confidence actions from the ingested evidence, it must return a blocked result instead of filler tasks

## Sources and activity

`Know More` and `Sources & Jobs` now read from worker-generated workspace data:

- recent ingested source snapshots
- recent signal-derived activity
- compressed market summary
- competitive position snapshot
- monitor job status
- structured knowledge cards
- editable draft knowledge segments
- source-level takeaway and business impact summaries
- knowledge feedback state

The frontend must not invent source inventory or recurring job history.
The frontend also restores the latest saved project and result for the current anonymous session through `GET /api/session/[sessionId]/state`.

`Sources & Jobs` is a real management surface, not a passive readout. It now supports:

- add, edit, pause, resume, and delete for sources
- add, edit, pause, resume, and delete for jobs
- visible last run, last result summary, and current status for sources
- visible trigger type, schedule, last three runs, last action summary, and expected impact summary for jobs

The app remains thin: these CRUD operations proxy to the Mac mini worker and read back worker-managed state.

For rich sources such as uploaded market-analysis documents:

- `Checklist` may still block if no action-quality move is justified
- `Know More` must still populate with synthesized knowledge cards that explain:
  - the insight
  - the implication
  - the next potential moves
- `Know More` must also surface the drafted knowledge segments created from the full source set
- ingested source cards must show why the source matters:
  - key takeaway
  - business impact
  - linked checklist tasks if any
  - confidence
- task explanation must stay in task detail, not in `Know More`

## Output safety

- `expected_advantage` remains strictly validated for measurable business effect
- weak but repairable task impacts are rewritten on the worker before final validation
- if repair is not possible, the worker must return a blocked result such as `insufficient_output_quality`
- the UI must not expose raw internal validation errors to the user

## Local development

```bash
cd /Users/chappie/Projects/Agent.Chappie/apps/consultant-followup-web
cp .env.example .env.local
npm install
npm run dev
```

## Vercel deployment target

- deploy only `apps/consultant-followup-web`
- keep secrets in Vercel project settings
- do not deploy the core runtime to Vercel
