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

## Vercel deployment notes

- root directory: `apps/consultant-followup-web`
- framework: Next.js
- keep the Mac mini worker private
- keep app secrets in Vercel env settings only
- `POST /api/jobs` is the app-side bridge entrypoint
- in worker mode, the app forwards jobs to the Mac mini worker over HTTP with `x-agent-shared-secret`

## Auth status

Auth is intentionally deferred in Phase 4. This app is a public test surface and should only use demo-safe inputs.
