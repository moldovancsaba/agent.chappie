# Handoff: 2026-03-25 Phase 8 / 3steps — Architect decisions

## Context

The learning loop is **mechanically real** but **not production-credible** until replacement quality, comment depth, reversibility, anti-overfitting, and **app/API path proof** meet the bar. Chat is no longer sufficient as the only record; **the repo carries current truth**.

**Product:** **3steps** — first app on Agent.Chappie (ingest user context + external signals, learn locally, return exactly **3** next best actions, regenerate on feedback).

## Architect decisions (working decision sheet)

1. **Commit Phase 8 to `docs/` now** — roadmap, handoff, app/runbook, task-action vocabulary, acceptance criteria. Clean pass; no over-design.
2. **Define Feedback v2 / worker feedback envelope now** (during Phase 8), not after proof — see [`docs/09_contracts/feedback_v2.md`](../09_contracts/feedback_v2.md).
3. **Automated proof with captured artifacts** — e2e where feasible; unit + integration + deterministic API tests **in CI**; fragile live model/internet cases **not** required in CI.
4. **Canonical `task_strength`** — `strong_action` | `tactical_action` | `exploratory_action`; reflected subtly in UI (chip/metadata); no heuristic-only disguise.
5. **Beta reversibility** — inspect learned negatives for project + **remove one** signal + **undo last teach** (undo-last alone insufficient).
6. **Decay / caps** — developer picks initial defaults + rationale; Architect reviews after implementation; **do not block coding** on pre-approval of constants.
7. **Sprint deps** — Pass 1 / M1 first; Pass 2–3 / M5–M6 may overlap; Pass 4 (rich-source) may start once M1 stable.
8. **Beta-ready sign-off** — developer + architect + product owner; **reference workflow** required (one consultant, one project, real sources, full feedback cycle, verify improvement).
9. **Doc hygiene** — fix minor contradictions immediately (e.g. Neon vs local brain for observations); hygiene yes, silent architectural scope shift no.
10. **Milestone artifact** — produced **before** M1 completes: [`docs/phase8_milestones_and_gates.md`](../phase8_milestones_and_gates.md).

## Immediate developer deliverables

1. Phase 8 / 3steps in docs (this handoff + roadmap + milestones + app/runbook + `feedback_v2`).
2. Implement learning-loop hardening per milestones.
3. Wire and use **feedback v2** consistently.
4. Add `task_strength` and reversible learning + bounded memory.
5. Automated tests + captured proof artifacts; app-path proof for three feedback modes.

## What not to do

Do **not** redesign architecture, move logic to the frontend, add auth or chat, broaden formats, or introduce global cross-project learning. Keep worker and local brain authoritative and the app thin.

## References

- Milestones and gates: [`docs/phase8_milestones_and_gates.md`](../phase8_milestones_and_gates.md)
- Task feedback contract: [`docs/09_contracts/feedback_v2.md`](../09_contracts/feedback_v2.md)
- App: [`docs/12_apps/consultant_followup_web.md`](../12_apps/consultant_followup_web.md)
- Runbook: [`docs/07_runbooks/consultant_followup_web.md`](../07_runbooks/consultant_followup_web.md)

## Agent Work Rule

When you are done with a bucket of tasks, always provide a full plain text summary that can be easily copied and pasted for the Architect to review.
