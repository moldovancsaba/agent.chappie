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
