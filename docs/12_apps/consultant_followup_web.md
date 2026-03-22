# Consultant Follow-Up Web App

## Purpose

This is the first thin app layer for Agent.Chappie. It exists to exercise the accepted contract layer in a public test MVP without adding auth, scheduler implementation, or core orchestration into the app.

## What the app does

- accepts one demo-safe client project summary
- accepts one raw competitive context input
- submits one `Job Request v1`
- retrieves one `Job Result v1`
- submits one `Feedback v1`
- presents the product as a single decision surface, not a dashboard

## Surface structure

The app now uses three sections only:

- `Your Checklist` as the default view with exactly 3 ranked task cards
- `Know More` as compressed read-only intelligence behind the checklist
- `Sources & Jobs` as the operator-side ingestion and recurring-job surface

The main checklist view must:

- show cards, not tables
- show exactly 3 visible task cards
- expose decision actions as `Done`, `Adjust`, and `Reject`
- include a confidence indicator for the current ranked output

## What the app does not do

- no login
- no OIDC or SSO integration in Phase 4
- no direct model calls
- no scheduler logic
- no public exposure of the Mac mini core
- no direct UI for internal observations

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

Phase 5 upgrades the app to support the first real private worker bridge while keeping the worker private:

`Vercel app -> durable data layer -> private worker on the Mac mini`

The app-side bridge entrypoint is:

- `POST /api/jobs`

The worker remains protected by a shared-secret header and returns only user-facing ranked tasks.

Shared state can still live in Neon for the app layer, but internal intelligence state remains local to the Mac mini worker.

## Observation model

The app now depends on a two-layer intelligence model:

- hidden `SystemObservation v1` signals persisted on the worker side
- visible ranked `recommended_tasks` returned to the app

The app must not expose the internal observation layer directly.

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
