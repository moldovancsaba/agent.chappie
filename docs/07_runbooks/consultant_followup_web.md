# Runbook: Consultant Follow-Up Web App

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
AGENT_LOCAL_DB_PATH=runtime_status/agent_brain.sqlite3
DEMO_STORAGE_MODE=memory
DATABASE_URL=postgres://user:password@host/database?sslmode=require
```

## Frontend boundary

The frontend now submits only raw source material.

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
- generating recent source/activity data for the app
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
- `monitor_state`
- `managed_sources`
- `managed_jobs`

## Vercel deployment notes

- root directory: `apps/consultant-followup-web`
- framework: Next.js
- keep the Mac mini worker private
- keep app secrets in Vercel env settings only
- `POST /api/jobs` is the app-side bridge entrypoint
- `GET /api/session/[sessionId]/state` restores the latest saved project and result for the current anonymous session
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

## Sources & Jobs behavior

The app now treats `Sources & Jobs` as a management surface:

- sources can be added, edited, paused, resumed, and deleted
- jobs can be added, edited, paused, resumed, and deleted
- source cards expose current status, last run, and last extracted summary
- job cards expose trigger type, schedule, last three runs, last action summary, and expected impact summary

The app must never invent this state locally. All CRUD actions proxy to the worker and re-render from worker responses.

## Auth status

Auth is intentionally deferred in Phase 4. This app is a public test surface and should only use demo-safe inputs.
