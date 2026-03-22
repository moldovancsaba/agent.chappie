# Consultant Follow-Up Web App

## Purpose

This is the first thin app layer for Agent.Chappie. It exists to exercise the accepted contract layer in a public test MVP without adding auth, scheduler implementation, or core orchestration into the app.

## What the app does

- accepts one demo-safe client project summary
- accepts one meeting-notes style context input
- submits one `Job Request v1`
- retrieves one `Job Result v1`
- submits one `Feedback v1`

## What the app does not do

- no login
- no OIDC or SSO integration in Phase 4
- no direct model calls
- no scheduler logic
- no public exposure of the Mac mini core

## Identity model for the public test

- `app_id` stays fixed as `app_consultant_followup`
- `project_id` is generated per demo project when needed
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

Phase 4 uses a demo bridge mode in the app layer so the public test can run without exposing the private Mac mini worker. This keeps the app runnable while preserving the long-term boundary:

`Vercel app -> durable data layer -> private worker on the Mac mini`

The demo bridge is intentionally a temporary implementation convenience, not a replacement for the core runtime.

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
