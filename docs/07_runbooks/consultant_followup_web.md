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
AGENT_BRIDGE_MODE=demo
AGENT_API_BASE_URL=http://127.0.0.1:8787
DEMO_STORAGE_MODE=memory
DATABASE_URL=postgres://user:password@host/database?sslmode=require
```

## Neon mode

1. apply the SQL in:
   `apps/consultant-followup-web/db/migrations/001_public_test_mvp.sql`
2. set:
   `DEMO_STORAGE_MODE=neon`
3. provide:
   `DATABASE_URL`

## Vercel deployment notes

- root directory: `apps/consultant-followup-web`
- framework: Next.js
- keep the Mac mini worker private
- keep app secrets in Vercel env settings only

## Auth status

Auth is intentionally deferred in Phase 4. This app is a public test surface and should only use demo-safe inputs.
