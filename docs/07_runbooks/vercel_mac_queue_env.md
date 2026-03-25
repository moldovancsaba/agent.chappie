# Copy-paste env: Vercel (queue mode) + Mac Mini consumer

Use this when the hosted app talks to **Neon only** and the Mac Mini **pulls** jobs (no Cloudflare, no `AGENT_API_BASE_URL` on Vercel).

Generate one long random secret (for example `openssl rand -hex 32`) and use the **same** value for `WORKER_QUEUE_SHARED_SECRET` on Vercel and on the Mac.

---

## 1. Vercel — Environment Variables

In the Vercel project: **Settings → Environment Variables**. Add for **Production** (and Preview if you use the same Neon DB there).

```bash
# Public (browser)
NEXT_PUBLIC_APP_NAME=Agent.Chappie Demo
NEXT_PUBLIC_APP_URL=https://YOUR-PRODUCTION-DOMAIN

# App identity
APP_ID=app_consultant_followup

# No direct HTTP to Mac — ignores AGENT_API_BASE_URL even if present
AGENT_BRIDGE_MODE=queue

# Durable queue + job results in Neon
DEMO_STORAGE_MODE=neon
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DB?sslmode=require

# Mac consumer authenticates to /api/worker/jobs/*
WORKER_QUEUE_SHARED_SECRET=PASTE-SAME-SECRET-AS-MAC

# Optional: only if some route still reads it; not used for worker HTTP in queue mode
# AGENT_SHARED_SECRET=PASTE-SAME-AS-WORKER_QUEUE_OR_LEAVE_UNSET
```

**Remove or leave unset on Vercel:** `AGENT_API_BASE_URL` (do not point at trycloudflare or a Mac URL).

---

## 2. Mac Mini — shell (before `worker_queue_consumer.py`)

From the **Agent.Chappie repo root** (adjust paths and URL):

```bash
source .venv/bin/activate

export APP_QUEUE_BASE_URL=https://YOUR-PRODUCTION-DOMAIN
export WORKER_QUEUE_SHARED_SECRET=PASTE-SAME-SECRET-AS-VERCEL
export AGENT_LOCAL_DB_PATH=runtime_status/agent_brain.sqlite3

# Optional: poll interval seconds (default 3)
# export WORKER_QUEUE_POLL_SECONDS=3

python scripts/worker_queue_consumer.py
```

`APP_QUEUE_BASE_URL` must be the **origin only** (no trailing path): the script calls `…/api/worker/jobs/claim` and `…/api/worker/jobs/<id>/complete|fail`.

### Production new source → Mac → back online: the three steps

This is the **only** path when the user adds a source on **production** with `AGENT_BRIDGE_MODE=queue` and `DEMO_STORAGE_MODE=neon`. It is implemented in code; there are no alternate hidden channels.

1. **Hosted write (Vercel + Neon)**  
   The browser calls the Next.js API (e.g. `POST /api/projects/{projectId}/sources`). Because direct worker HTTP is off, the handler **does not** call the Mac. It inserts (or updates) a row in **`demo_job_queue`** with `status = 'queued'`, plus JSON columns **`job_request`** and **`source_package`** (the full payload: text, metadata, and base64 file bytes when applicable). Nothing is written to the Mac yet.

2. **Mac pull, local brain, complete (Python + local SQLite)**  
   `scripts/worker_queue_consumer.py` loops: **`POST {APP_QUEUE_BASE_URL}/api/worker/jobs/claim`** with header **`x-agent-worker-secret`**. The API returns **204** if no queued row; otherwise it atomically sets the row to **processing** and returns **`job_request`** + **`source_package`**. The script runs **`process_job_payload`** from `worker_bridge.py`, which **reads and writes `AGENT_LOCAL_DB_PATH`** (SQLite): snapshots, observations, facts, cards, checklist result, etc. On success it **`POST`s `/api/worker/jobs/{job_id}/complete`** with **`job_result`**; the server stores **`demo_job_results`** and **deletes** the row from **`demo_job_queue`**. Then it **`POST`s `/api/worker/projects/{project_id}/workspace`** with a built workspace JSON so the hosted app can render state without talking to SQLite.

3. **Hosted read (Vercel + Neon)**  
   The web app loads workspace / session state from **Neon** (snapshots, results), not from the Mac disk. If step 2 never completes or workspace sync fails, production stays stale even if SQLite on the Mac partially changed.

**Operations:** Run **one** `worker_queue_consumer.py` process per environment. Multiple copies still use `FOR UPDATE SKIP LOCKED`, but they waste CPU and complicate logs.

---

## 3. Local Next.js against Neon (optional)

`apps/consultant-followup-web/.env.local` for hitting a real queue from `npm run dev`:

```bash
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_APP_NAME=Agent.Chappie Demo
APP_ID=app_consultant_followup
AGENT_BRIDGE_MODE=queue
DEMO_STORAGE_MODE=neon
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DB?sslmode=require
WORKER_QUEUE_SHARED_SECRET=PASTE-SAME-SECRET-AS-MAC
```

Run the Mac consumer with `APP_QUEUE_BASE_URL=http://localhost:3000` when testing locally.
