# READMEDEV

## Phase 8 / 3steps

Implement against: [`docs/phase8_milestones_and_gates.md`](phase8_milestones_and_gates.md), [`docs/09_contracts/feedback_v2.md`](09_contracts/feedback_v2.md), app doc [`docs/12_apps/consultant_followup_web.md`](12_apps/consultant_followup_web.md).

## Documentation-first operating rules (mandatory)

- **Do not assume.** If behavior is not explicitly documented, treat it as unknown.
- **Document before/with implementation.** Contract, boundary, and runbook updates are required whenever behavior changes.
- **Use docs actively while working.** Align implementation to existing docs (`architecture`, `contracts`, `runbooks`, `handoffs`, `roadmap`) and cite them in handoffs.
- **Clarify before action when uncertain.** If ambiguity remains after reading docs and code, ask the Architect/Product Owner before implementation.
- **No silent divergence.** If code and docs disagree, either fix docs as hygiene (no scope change) or escalate for clarification (scope/architecture).
- **Proof is required.** No task is complete without deterministic evidence (tests, API artifacts, persistence evidence) recorded in docs/handoffs.

## Clarification protocol

Before major implementation work:

1. Read relevant docs in `docs/`.
2. Verify current code path.
3. Identify mismatches/unknowns.
4. Ask clarifying questions if any unknown materially affects behavior.
5. Then implement and document.

## Agent Work Rule

When you are done with a bucket of tasks, always provide a full plain text summary that can be easily copied and pasted for the Architect to review.
