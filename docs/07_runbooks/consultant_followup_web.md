# Runbook: Consultant Follow-Up Web App

**Product:** **3steps** (first app). Phase **8** delivery plan and gates: [`docs/phase8_milestones_and_gates.md`](../phase8_milestones_and_gates.md). Task feedback contract: [`docs/09_contracts/feedback_v2.md`](../09_contracts/feedback_v2.md).

## Task actions and proof (Phase 8)

- Use **`feedback_v2`** `action_type` values: `done`, `edit`, `decline_and_replace`, `delete_only`, `delete_and_teach`, `hold_for_later`; optional `comment`.
- Tasks must expose **`task_strength`**: `strong_action` | `tactical_action` | `exploratory_action` in API payloads and subtle UI.
- **Beta learning controls:** inspect learned negatives for the project, remove one mistaken signal, undo most recent teach — via app/API, not raw SQLite.
- **Proof:** capture raw request/response JSON, before/after tasks, DB rows for `decline_and_replace`, `delete_and_teach`, and comment-driven regeneration through **Next.js API**.
- **CI:** unit + integration + deterministic API-boundary tests must run in CI; fragile live-model/internet cases may stay out of CI with artifacts captured separately.

## Job execution model (Phase 8)

For job submission, the app now follows:

`Vercel app/API -> durable database queue -> Mac mini worker consumer -> result written back to DB -> app polls result`

`POST /api/jobs` **only enqueues** (`enqueueJobForWorker` → in-memory queue or Neon `demo_job_queue`). It does **not** run the Python worker inside Next.js. A **queue consumer** (`scripts/worker_queue_consumer.py`) must claim jobs and call `process_job_payload`; see **[Webapp input → automatic tasks](#webapp-input--automatic-tasks-end-to-end)** below.

### Production without Cloudflare (no inbound tunnel)

You do **not** need `AGENT_API_BASE_URL` or a Cloudflare tunnel on Vercel. Jobs and completed results are **temporary online state** in Neon; the Mac Mini **pulls** work and writes results back over HTTPS to your hosted app.

Set on Vercel (or `.env.local` for a Neon-backed dev deploy):

- `AGENT_BRIDGE_MODE=queue` — disables all server-side HTTP to a private Mac worker; `AGENT_API_BASE_URL` is ignored even if set.
- `DEMO_STORAGE_MODE=neon` and `DATABASE_URL=...`
- `WORKER_QUEUE_SHARED_SECRET=...` (same value on the Mac consumer)

On the Mac Mini, run `scripts/worker_queue_consumer.py` with `APP_QUEUE_BASE_URL=https://<your-production-app>` and the same queue secret. The consumer runs the real worker locally and persists to `AGENT_LOCAL_DB_PATH`; the hosted app only sees job rows and `JobResult` JSON.

Workspace panels in the browser are synthesized from the latest stored `JobResult` for that project (not the full Mac SQLite workspace). Features that mutate workspace entities over HTTP to the Mac return a clear error in `queue` mode.

**Ready-to-paste env blocks:** [`vercel_mac_queue_env.md`](vercel_mac_queue_env.md).

### Webapp input → automatic tasks (end-to-end)

This is the **only** path from “something the operator adds in the browser” to **three `recommended_tasks`** in `JobResult v1`, for the shipped consultant app.

| Operator action (UI) | Next.js route | What gets stored | Who produces tasks |
| --- | --- | --- | --- |
| **First-run / main composer:** paste URL, text, or upload a file and run | `POST /api/jobs` | `demo_jobs` row + **`demo_job_queue`** row (`job_request` + `source_package`: raw text, optional base64 file) | Mac (or any host) running **`worker_queue_consumer.py`**: `process_job_payload` |
| **Sources & Jobs:** add source (same modes: URL / text / file) while `AGENT_BRIDGE_MODE=queue` | `POST /api/projects/{projectId}/sources` | Same queue shape; `source_ref` like `managed_source_*` | Same consumer |

**Not automatic (no new three-task generation by itself):**

- Editing knowledge cards, deleting/holding segments, or task feedback **without** a new ingestion job: those paths update feedback or call regeneration APIs where implemented; they do **not** replace the queue+consumer contract above.
- `AGENT_BRIDGE_MODE=queue`: CRUD on sources/jobs that would require **direct HTTP** to `worker_bridge.py` on the Mac is **blocked** in the hosted app (see `describeDirectWorkerBlock()`). **Adding a source via the queue path still enqueues a full processing job** and is the supported way to refresh checklist + workspace on production.

**Inside `process_job_payload` (single job run):**

1. **Ingest** — Normalize `source_package` into snapshots, observations, facts, evidence units (local SQLite `AGENT_LOCAL_DB_PATH`).
2. **Flashcards / {trinity}** — When `FLASHCARD_MLX_TRINITY=1`, Trinity MLX builds **intelligence cards**; otherwise heuristic cards (strict prod may **block** if Trinity is mandatory and fallback is off). Cards are scored, stored, and **top 20%** drive “visible” cards; **all scored cards** feed ranking. See [`trinity_architecture.md`](../trinity_architecture.md).
3. **{knowmore} corpus** — `knowledge_cards`, `draft_segments`, and **`intelligence_cards`** are written; workspace sync sends them to the hosted app (`POST /api/worker/projects/{projectId}/workspace`).
4. **Three tasks** — The worker builds a segment-style checklist, then **when valid**, replaces the result with **NBA tasks materialized from ranked intelligence cards**: each top card becomes a synthetic segment → **`segment_to_task`** (same execution steps / validation as the normal checklist) → **`judge_tasks`**, with ordering biased toward primary-signal competitors and comparison-surface language. Tasks may include **`intel_card_id`** and `evidence_refs` entries `intel_card::{id}`; the web checklist shows **From {knowmore}** when `intel_card_id` is present.
5. **Back to the webapp** — Consumer **`POST`s `/api/worker/jobs/{job_id}/complete`** with `job_result` (Neon `demo_job_results`). The UI polls **`GET /api/jobs/{job_id}`** until status is no longer 202 queued.

**Requirements for “upload a document → tasks appear”:**

- `DEMO_STORAGE_MODE=neon` + `DATABASE_URL` on Vercel (or memory queue for local-only dev with consumer pointed at `localhost`).
- `AGENT_BRIDGE_MODE=queue` on production.
- **`WORKER_QUEUE_SHARED_SECRET`** matching on Vercel and the consumer host.
- Consumer running with `APP_QUEUE_BASE_URL`, `AGENT_LOCAL_DB_PATH`, and (for Trinity) MLX env vars documented in [`trinity_architecture.md`](../trinity_architecture.md).

### Mac watchdog: queue consumer health

LaunchAgent **`com.agentchappie.watchdog`** runs `scripts/watchdog_agent.py` on an interval (see `ops/com.agentchappie.watchdog.plist`). Flags:

- **`--check-queue-consumer`** — counts `worker_queue_consumer.py` PIDs, logs JSON lines to `runtime_status/queue_consumer_health.jsonl`, and appends notable events to `watchdog_log.jsonl`.
- **`--remediate-duplicate-consumers`** — if **more than one** consumer is running, **SIGTERM** extras and keep the **lowest PID**.

After pulling repo changes to the plist, re-run **`scripts/install_services.sh`**. Exit codes from the script: **4** = no consumer; **5** = duplicate consumers (should clear after remediation). See also [`docs/02_stack.md`](../02_stack.md) for **exact LLM vs non-LLM** roles (orchestrator Ollama drafter/writer/judge vs deterministic consultant worker).

## Card intelligence pipeline (source -> facts -> cards -> scores -> tasks)

**MLX Trinity (optional):** When `FLASHCARD_MLX_TRINITY=1`, flashcards are produced by the local three-model Trinity path. **Heuristic fallback is off by default:** set `AGENT_ALLOW_HEURISTIC_FLASHCARDS=1` on dev machines if Trinity fails (MLX missing, timeout, empty rows) and you still want legacy heuristic cards instead of a **blocked** job. **Hard timeout kill:** set `TRINITY_SUBPROCESS=1` with `TRINITY_MAX_WALL_SECONDS>0` to run Trinity in a child process (see [`trinity_architecture.md`](../trinity_architecture.md) §8). **Preflight:** `python3 scripts/trinity_healthcheck.py` (optional `--quick`). Architecture, env tables, and roadmap: [`docs/trinity_architecture.md`](../trinity_architecture.md), [`docs/trinity_flow.md`](../trinity_flow.md) Appendix A, [`docs/03_roadmap.md`](../03_roadmap.md).

The worker now runs a strict three-layer flow:

1. **Drafter**: extract atomic facts (traceable, one clause/observation per fact) and aggregate stats.
2. **Writer**: build business flashcards from atomic facts + KYC context.
3. **Judge**: score each card (`confidence`, `impact_score`, `freshness`, `expires_at`) and rank.

Visibility rule:

- All cards are stored in local brain tables (`atomic_facts`, `intelligence_cards`, `card_scores`).
- App-visible flashcards are the dynamic top 20% by weighted rank.
- Recommendations are generated from **all** cards, weighted by confidence * impact * urgency.

### End-to-end example

**Input source (excerpt)**

- "341 competitor soccer clubs in our market list."
- "No club uses monthly subscription; all use seasonal/upfront packages."
- "Offer-heavy pages focus on trial + onboarding waiver."

**Atomic facts (drafter output)**

```json
[
  { "fact_type": "entity", "fact_key": "competitor", "fact_value": { "name": "Essex County Club" } },
  { "fact_type": "entity", "fact_key": "competitor", "fact_value": { "name": "FlowOps" } },
  { "fact_type": "stat", "fact_key": "competitor_count", "fact_value": { "value": 341 } },
  { "fact_type": "stat", "fact_key": "subscription_model_present", "fact_value": { "value": false } },
  { "fact_type": "stat", "fact_key": "signal_type_count", "fact_value": { "signal_type": "offer", "value": 27 } }
]
```

**Flashcards (writer output)**

```json
[
  {
    "insight": "341 competitors/entities are currently represented in your market evidence set.",
    "implication": "The comparison field is crowded; differentiation and channel-specific proof need to be explicit.",
    "potential_moves": [
      "Build a competitor map focused on the highest-pressure segment this week.",
      "Add one direct comparison block where buyers evaluate alternatives."
    ],
    "fact_refs": ["fact::...::competitor_count"],
    "source_refs": ["managed_source_src_..."]
  },
  {
    "insight": "No subscription model signal appears in the current market evidence.",
    "implication": "Recurring pricing can be a potential asymmetry if buyer fit and onboarding friction are handled.",
    "potential_moves": [
      "Test one recurring offer variant for the highest-likelihood segment.",
      "Publish a side-by-side recurring vs legacy payment comparison."
    ],
    "fact_refs": ["fact::...::subscription_model_present"],
    "source_refs": ["managed_source_src_..."]
  }
]
```

**Judge scores**

```json
{
  "card_id": "card::demo_project::2",
  "confidence": 0.82,
  "impact_score": 78,
  "freshness_score": 0.71,
  "expires_at": "2026-03-29T00:00:00Z",
  "rank_score": 0.79
}
```

**Final task output (NBA from intelligence cards, materialized like segment tasks)**

Ranked cards are turned into **`recommended_tasks`** via **`build_nba_tasks_from_intelligence_cards`**: synthetic draft segment per card → **`segment_to_task`** → **`judge_tasks`**. Shapes match the full checklist task (e.g. `execution_steps`, `target_channel`, `intel_card_id` when card-sourced). If NBA materialization cannot yield three validated tasks, the worker keeps the **segment checklist** result instead.

```json
{
  "rank": 1,
  "title": "Add pricing comparison block and onboarding FAQ on pricing page this week before …",
  "why_now": "We detected pricing or onboarding pressure tied to …",
  "expected_advantage": "Increases conversion for active buyers this week by answering …",
  "evidence_refs": ["…", "intel_card::card:…"],
  "intel_card_id": "card:…",
  "best_before": "2026-03-27",
  "execution_steps": ["…", "…", "…", "…"]
}
```

## Troubleshooting: job stays queued / cannot submit context

1. Ensure app env is set in `apps/consultant-followup-web/.env.local`:
   - `DEMO_STORAGE_MODE=neon`
   - `DATABASE_URL=...`
   - `WORKER_QUEUE_SHARED_SECRET=...`

2. Start the Mac worker queue consumer (repo root):

   ```bash
   source .venv/bin/activate
   export APP_QUEUE_BASE_URL=https://agent-chappie.doneisbetter.com
   export WORKER_QUEUE_SHARED_SECRET=replace-me
   export AGENT_LOCAL_DB_PATH=runtime_status/agent_brain.sqlite3
   python scripts/worker_queue_consumer.py
   ```

3. If jobs remain queued, verify worker API auth secret matches between Vercel and Mac worker consumer (`WORKER_QUEUE_SHARED_SECRET`).
4. If queue claim succeeds but completion fails, inspect consumer output for `complete` / `fail` callback errors.

## Troubleshooting: `{knowmore}` flashcards are empty

In the **{knowmore}** tab, the UI shows:

- a flashcard pipeline line (`Flashcard pipeline: …`) from `latest_flashcard_pipeline_run`
- a visible flashcard deck (top 20% · `state === "active"`)
- an optional “Quarantined flashcards” deck (`state === "quarantine"`)

Use this to pinpoint the failure:

1. Check the pipeline line in the UI:
   - `pipeline_source: trinity_disabled`: heuristic flashcards were used; you should see visible flashcards.
   - `pipeline_source: heuristic_fallback`: Trinity was on but failed; heuristic fallback generated cards; you should see cards.
   - `pipeline_source: trinity_strict_blocked`: Trinity is enabled and heuristic fallback is forbidden; the worker returned no usable cards, so **{knowmore} can be empty**.
2. If the pipeline line shows `trinity_strict_blocked`:
   - fix MLX/Trinity readiness, or
   - allow heuristic fallback on the Mac worker by setting `AGENT_ALLOW_HEURISTIC_FLASHCARDS=1`, or
   - disable Trinity by unsetting `FLASHCARD_MLX_TRINITY`.
3. If the pipeline line shows `trinity_disabled` / `heuristic_fallback` but still no flashcards:
   - confirm the Mac worker queue consumer is running (`scripts/worker_queue_consumer.py`)
   - confirm workspace sync succeeds in the consumer logs (`[sync] workspace pushed …`)
   - verify your job finishes with `scheduler_state: complete` in `GET /api/jobs/{job_id}`.

## Local development

```bash
cd /Users/chappie/Projects/Agent.Chappie/apps/consultant-followup-web
cp .env.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Local environment variables

```bash
NEXT_PUBLIC_APP_NAME=Agent.Chappie Demo
NEXT_PUBLIC_APP_URL=http://localhost:3000
APP_ID=app_consultant_followup
AGENT_BRIDGE_MODE=worker
AGENT_API_BASE_URL=http://127.0.0.1:8787
AGENT_SHARED_SECRET=replace-me
WORKER_QUEUE_SHARED_SECRET=replace-me
AGENT_LOCAL_DB_PATH=runtime_status/agent_brain.sqlite3
DEMO_STORAGE_MODE=memory
DATABASE_URL=postgres://user:password@host/database?sslmode=require
```

## Frontend boundary

The frontend now submits only raw source material.

## UI reference

The current shell/theme direction intentionally follows the reference repo:

- `moldovancsaba/remix-of-gtm-ai-navigator`

Adoption rules:

- match the reference's darker left rail, cooler command-center palette, and tighter SaaS card styling
- keep a visible workspace context bar above the active surface so operators can see focus and volume at a glance
- keep section-level count badges and sticky secondary reasoning panels on desktop so long pages stay usable
- preserve Agent.Chappie's product structure and product rules
- do not import dashboard clutter, fake analytics, or generic admin framing
- keep the current views:
  - `Checklist`
  - `Know More`
  - `Sources & Jobs`
- keep user-facing language as `We` to `You`

## Developer correction policy

For this app, patching around symptoms is forbidden.

- only root-cause fixes are acceptable
- do not ship UI masking, wording-only coverups, or fallback hacks in place of a true fix
- if source cards, checklist items, knowledge cards, or workspace state are missing in the UI, the fix must trace the real failure through storage, API response, session recovery, frontend state, and rendering
- every production correction must document:
  - the real failure mode
  - the root cause
  - the real fix

Do not add frontend fields for:

- project summary
- competitor
- region
- synthetic source inventory
- synthetic recurring jobs

Those are generated or maintained on the Mac mini worker.

The frontend may submit:

- one pasted URL
- one raw text block
- one uploaded document

The Mac mini worker is responsible for:

- fetching URL content
- extracting supported document text
- normalizing ingested source material
- recovering project context from the local brain
- drafting persistent knowledge segments from the full source set
- writing business-value tasks from those segments and linked evidence
- judging the task set into ranked next-best-action output
- generating recent source/activity data for the app
- generating structured knowledge cards for `Know More`
- keeping task detail separate from the global knowledge surface
- repairing weak-but-salvageable task impacts before final validation
- returning a blocked result instead of leaking raw validation failures

## Neon mode

Neon remains for app-visible shared state only:

- projects
- jobs
- job results
- feedback

Neon is not the authoritative store for `system_observations`.

1. apply the SQL in:
   `apps/consultant-followup-web/db/migrations/001_public_test_mvp.sql`
2. set:
   `DEMO_STORAGE_MODE=neon`
3. provide:
   `DATABASE_URL`
4. run the private worker locally:

```bash
cd /Users/chappie/Projects/Agent.Chappie
cp .env.example .env.local
source .venv/bin/activate
python scripts/worker_bridge.py
```

## Local worker brain

The authoritative internal intelligence store lives on the Mac mini in:

- `AGENT_LOCAL_DB_PATH`, defaulting to `runtime_status/agent_brain.sqlite3`

This local SQLite database stores:

- `system_observations`
- `source_snapshots`
- `project_knowledge_state`
- `draft_knowledge_segments`
- `monitor_state`
- `managed_sources`
- `managed_jobs`
- `task_feedback`
- `replacement_history`

## Worker service

The private worker must run as a supervised local service, not as a manual terminal process.

- launch agent label: `com.agentchappie.worker`
- launch agent path: `/Users/chappie/Library/LaunchAgents/com.agentchappie.worker.plist`
- health check: `curl http://127.0.0.1:8787/health`
- stdout log: `runtime_status/worker_stdout.log`
- stderr log: `runtime_status/worker_stderr.log`

Recommended lifecycle:

```bash
launchctl bootout gui/$(id -u) /Users/chappie/Library/LaunchAgents/com.agentchappie.worker.plist 2>/dev/null || true
launchctl bootstrap gui/$(id -u) /Users/chappie/Library/LaunchAgents/com.agentchappie.worker.plist
launchctl kickstart -k gui/$(id -u)/com.agentchappie.worker
```

## Vercel deployment notes

- root directory: `apps/consultant-followup-web`
- framework: Next.js
- keep the Mac mini worker private
- **Documented product boundary** (see [`docs/01_architecture.md`](../01_architecture.md)): `Vercel app/API → durable database/job layer → private Mac mini worker`. The Mac is **not** meant to be the public edge; the online DB is the handoff between the app and the worker.
- **What the shipped app does today:** `POST /api/jobs` calls **`enqueueJobForWorker`** only (see [`apps/consultant-followup-web/app/api/jobs/route.ts`](../../apps/consultant-followup-web/app/api/jobs/route.ts)). It does **not** call `runWorkerJob` from that route. With **`AGENT_BRIDGE_MODE=queue`** and **`DEMO_STORAGE_MODE=neon`**, jobs land in **`demo_job_queue`**; **`scripts/worker_queue_consumer.py`** on the Mac **claims** via `POST /api/worker/jobs/claim`, runs **`process_job_payload`**, then **`POST`s complete** and **workspace sync**. The UI waits on **`GET /api/jobs/{jobId}`** (202 while queued/processing).
- **Legacy / dev alternative:** `AGENT_BRIDGE_MODE=worker` with **`AGENT_API_BASE_URL`** set allows **other** server routes to call the Mac over HTTP (`runWorkerJob` exists in `worker-bridge.ts` for that pattern); production Vercel should prefer **queue** so no inbound tunnel is required.
- keep app secrets in Vercel env settings only
- `POST /api/jobs` is the app-side **enqueue** entrypoint for the main composer
- `GET /api/session/[sessionId]/state` restores the latest saved project and result for the current anonymous session
- if the restored result still contains known stale legacy task phrasing, the app now asks the worker to regenerate the checklist from the current local brain before returning that result
- `GET /api/projects/[projectId]/workspace` reads worker-generated source and activity state
- `POST /api/projects/[projectId]/sources` adds a managed source
- `PATCH /api/projects/[projectId]/sources/[sourceId]` edits or pauses a managed source
- `DELETE /api/projects/[projectId]/sources/[sourceId]` removes a managed source
- `POST /api/projects/[projectId]/jobs` adds a managed job
- `PATCH /api/projects/[projectId]/jobs/[jobId]` edits or pauses a managed job
- `DELETE /api/projects/[projectId]/jobs/[jobId]` removes a managed job
- in worker mode, the app forwards jobs to the Mac mini worker over HTTP with `x-agent-shared-secret`
- the deployed app should remain free of sample business data and fabricated context entries
- supported document uploads are currently: `.txt`, `.md`, `.csv`, `.pdf`, `.docx`
- unsupported document or media formats should be rejected honestly, not shown as parsed

## Pressure testing

Phase 7 pressure testing is now a first-class runbook step.

Run:

```bash
cd /Users/chappie/Projects/Agent.Chappie
source .venv/bin/activate
python scripts/pressure_test_worker.py
```

Artifacts are written to:

- `runtime_status/pressure_tests/phase7_pressure_report.md`
- `runtime_status/pressure_tests/phase7_pressure_report.json`

The report must be used to identify:

- strongest cases
- weakest cases
- repeated task-quality failures
- where the third task is still falling back to an information request

## Sources & Jobs behavior

The app now treats `Sources & Jobs` as a management surface:

- sources can be added, edited, paused, resumed, and deleted
- jobs can be added, edited, paused, resumed, and deleted
- the delete model now has 4 explicit operator paths:
  - `Delete`
  - `Delete and teach`
  - `Hold for later`
  - `Remove source and rebuild`
- live checklist task cards now expose the same delete model:
  - `Delete` removes the task from the live set without teaching
  - `Delete and teach` removes the task and stores what We should avoid
  - `Hold for later` removes the task from the live set and treats it as not timely now
  - `Remove source and rebuild` removes the linked source evidence and rebuilds from what remains
- source cards expose current status, last run, and last extracted summary
- ingested source cards expose:
  - key takeaway
  - business impact
  - linked checklist tasks
  - confidence
  - source-level actions such as reprocess, edit metadata, and delete
- job cards expose trigger type, schedule, last three runs, last action summary, and expected impact summary
- knowledge cards now support:
  - silent delete without teaching
  - delete with annotation so We record what to avoid
  - hold for later so the card leaves the live surface and returns to draft/parking state
- draft knowledge segment cards now support the same operator controls:
  - `Delete`
  - `Delete and teach`
  - `Hold for later`
  - `Remove source and rebuild` when a source still anchors the segment

The app must never invent this state locally. All CRUD actions proxy to the worker and re-render from worker responses.
Use `We` for the service voice and `You` for the operator in all user-facing copy.
Do not ship detached internal product language such as `the worker` or `the user` on visible screens.
Task feedback must save automatically from the action button or text-field blur. Do not require a second `Submit decisions` step after the operator already clicked the task action.

## Highest-priority unresolved behavior

The most important unfinished behavior is the task-side learning loop.

In plain English:

- if You reject a task, We should replace it immediately
- if You delete a task and explain why, We should remember that reason and stop repeating the same kind of weak task as often
- if You comment on a task, the regenerated replacement should change because of that comment
- if You edit a task, that edit should become a preferred pattern for similar future tasks
- after replacement, the checklist should still stay at exactly 3 tasks

Do not treat minor UI polish as more important than this.
The system is already usable enough to expose this as the next real product bottleneck.

## Knowledge surface behavior

- `Checklist` is action-only
- `Task Detail` is one-to-one with a single checklist action
- `Know More` is the structured knowledge surface
- `Know More` should lead with worker-generated strategic synthesis such as a competitive position snapshot
- `Know More` should surface worker-drafted knowledge segments created from the complete source set
- the worker should persist atomic `evidence_units` so one source can feed multiple knowledge cards and multiple sources can strengthen one card
- those evidence units should preserve explicit channel, section, asset, and claim details when the source contains them
- high-signal source clauses with explicit action structure should become evidence units too, not just fact-chip or observation derivatives
- draft segments should now include unit-cluster-derived segments before broader card-level summaries
- key knowledge cards such as pricing, offer/positioning, and proof should prefer action-aware unit clusters for their visible items
- the worker should rebuild `market_summary`, `competitors_detected`, `pricing_packaging`, `offer_positioning`, `proof_signals`, and `open_questions` from clustered evidence units instead of broad source blur
- when Agent.Chappie can fetch missing public-web competitor context itself, that enrichment should happen automatically and be stored in the local brain before the system asks the operator to research anything
- auto-collected enrichment must remain visually distinct from operator-provided sources in the UI
- each knowledge card should surface:
  - insight
  - implication
  - potential moves
  - confidence source
  - strongest supporting excerpt when available
  - supporting unit count
- knowledge edits must preserve auditability:
  - original value
  - user modification
  - timestamp

Task detail should be evidence-bundle-specific:

- use task-level supporting source refs when available instead of broad workspace source sets
- score task-supporting sources explicitly and exclude weak or off-theme sources before task detail renders
- persist and return per-task `supporting_source_scores` so the UI can surface the strongest support source first
- persist and return per-task `supporting_signal_scores` and `supporting_segment_scores` so task detail can order signals and draft segments by evidence strength too
- show strongest evidence excerpt when available
- show target channel, target segment, and done definition when the writer/judge provide them
- prefer worker-authored execution steps when available instead of frontend-only reconstruction
- worker-authored execution steps and done definitions should use the strongest excerpt, chosen competitor, and chosen channel so each task detail reads like a task-instance playbook
- if the winning evidence bundle contains an explicit asset, section, or claim, the worker should reuse that exact structure in the task title, execution steps, and done definition
- task titles, `why now`, and expected impact should also prefer explicit extracted claims and assets over generic audience/frame language when those details exist
- entity cleanup must reject imperative verbs such as `Add`, `Rewrite`, `Launch`, or `Publish` so task instructions cannot be misread as competitor names
- if the legacy observation engine and the bundle-authored segment writer both produce valid task sets, the worker should prefer the more specific bundle-authored set
- execution steps must be operational, not generic filler
- reopened job results must not replay stale generic task text if the current worker can regenerate a sharper checklist from the same project knowledge
- source-card takeaway and business-impact summaries should prefer action-aware source clusters over broad card blur when a source contains explicit asset/channel/claim structure
- the competitive snapshot should prefer those same action-aware clusters so it can talk about concrete assets and claims, not only broad pricing/offer pressure labels
- `Know More` should keep `Market Summary` at the higher pattern level and de-duplicate overlapping item text across the more specific pricing, offer/positioning, and proof cards

If a rich source is processed but no immediate action is strong enough:

- `Checklist` should still return exactly three tasks, using lower-confidence exploratory moves only after system-executed enrichment and stronger action synthesis have already been attempted
- `Know More` must still render worker-generated knowledge cards
- the blocked state should read like active monitoring, not failure
- the ingested source card must still show processing outcome and source-level value

## Auth status

Auth is intentionally deferred in Phase 4. This app is a public test surface and should only use demo-safe inputs.
