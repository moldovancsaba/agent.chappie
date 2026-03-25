# Phase 8 — 3steps: milestones, gates, and exit criteria

**Product name:** 3steps (first app on Agent.Chappie; consultant follow-up web surface).  
**Objective:** Ship a **production-credible action engine**: ingest context → generate 3 actions → learn from feedback → regenerate better actions → maintain operator trust.

**Canonical references:** [`handoff_20260325_phase8_3steps_architect_decisions.md`](08_handoffs/handoff_20260325_phase8_3steps_architect_decisions.md), [`feedback_v2.md`](09_contracts/feedback_v2.md), [`consultant_followup_web.md`](12_apps/consultant_followup_web.md), [`consultant_followup_web` runbook](07_runbooks/consultant_followup_web.md).

---

## Execution order (milestones)

1. **M1** — Learning loop hardening (core behavior)  
2. **M3** — Feedback contract v2 (define + wire)  
3. **M2** — Learning control (reversible + safe)  
4. **M4** — Replacement quality gate + `task_strength`  
5. **M5** — App/API path proof (critical gate)  
6. **M6** — Unified task action model (UI + behavior)  
7. **M7** — Reference workflow validation (beta gate)

**Sprint overlap (Architect):** M1 first. M5 and M6 may overlap with M2–M4 where sensible. Rich-source tightening (Pass 4 / M7 prep) may begin once M1 is stable.

---

## M1 — Learning loop hardening (core behavior)

**Scope:** `decline_and_replace`, `delete_and_teach` (semantic), comment-driven regeneration, duplicate suppression, replacement quality.

**Required components:**

- Jaccard or equivalent similarity guard (title ± structure as agreed in implementation)
- replacement selection across **different move buckets** before fallback
- exploratory fallback **only** after exhaustion of strong candidates

**Exit criteria:**

- Decline → replacement: not near-duplicate, not syntactically broken, different move pattern when possible
- Delete-and-teach: suppresses **similar** tasks, not exact string only
- Comment: changes at least one of move bucket, channel, or phrasing (when comment is specific enough)

**Proof:** before/after task arrays (JSON); similarity logs; example of rejected replacement candidate

---

## M2 — Learning control (reversible + safe)

**Scope:** inspect learned signals, **undo last teach**, **remove one specific** learned signal, bounded influence (decay + caps).

**Beta minimum (Architect):**

- view learned **negative** signals for current project
- delete **one** mistaken signal
- **undo most recent** teach action  
  (undo-last alone is **not** sufficient; inspect + delete one is required.)

**Required components:** API (or app-proxied) visibility into relevant local DB rows; fields for weight, decay/timestamp, caps.

**Exit criteria:** behavior changes after removal; no permanent irreversible poisoning from a few mistaken teaches.

**Proof:** DB rows before/after removal; visible regeneration difference after removal

---

## M3 — Feedback contract v2

**Scope:** Implement unified envelope per [`feedback_v2.md`](09_contracts/feedback_v2.md).

**Example shape:**

```json
{
  "action_type": "decline_and_replace | delete_only | delete_and_teach | hold_for_later | done | edit",
  "task_id": "...",
  "comment": "...",
  "project_id": "...",
  "submitted_at": "..."
}
```

**Exit criteria:** all task actions use this contract; persisted in local brain; consumed by generator.

**Proof:** raw request JSON; stored DB row; regeneration influenced by payload

---

## M4 — Replacement quality gate

**Scope:** Block weak or misleading replacements.

**Rules — replacement must NOT:**

- be near-duplicate (similarity > threshold)
- have broken phrasing
- reuse the same pattern after rejection without justification
- present as strong if it is exploratory

**Required:** `task_strength`: `strong_action` | `tactical_action` | `exploratory_action` on task payloads; UI shows distinction subtly.

**Proof:** one candidate rejected for similarity; one exploratory task correctly labeled

---

## M5 — App/API path proof (critical gate)

**Scope:** Prove behavior through **real Next.js** boundary.

**Cases:** (1) `decline_and_replace`, (2) `delete_and_teach`, (3) comment-driven regeneration.

**Per case:** raw request JSON, raw response JSON, before/after task arrays, DB entries, checklist **exactly 3**.

**Exit:** all three pass via app API, not worker-only scripts.

---

## M6 — Unified task action model (UI + behavior)

**Scope:** Every task card supports: Done, Edit, Decline & replace, Delete only, Delete & teach, Hold for later — mapped unambiguously to backend behavior.

**Exit:** consistent with [`feedback_v2.md`](09_contracts/feedback_v2.md); no ambiguity between delete-only vs teach.

---

## M7 — Reference workflow validation (beta gate)

**Scenario:** one consultant, one project, several **real** sources, one full cycle: generate → reject/comment/teach → regenerate → verify improvement.

**Acceptance:**

- learning: tasks improve; repeated mistakes drop
- output: ≥2/3 tasks strong or tactical when evidence exists; fallback labeled exploratory
- stability: always 3 tasks; no duplication; no broken phrasing
- trust: evidence valid; task detail actionable

**Sign-off:** developer (implementation + proof) + architect (credible behavior) + product owner (usable workflow). No beta-ready without this reference workflow passing.

---

## Non-goals (strict)

Do **not:** add auth; add chat; expand formats; redesign architecture; global cross-project learning; dashboard sprawl.

---

## Failure conditions (Phase 8 fails)

- replacement still near-duplicate; teach blocks exact strings only; comments ignored; learning irreversible; overfitting after few interactions; proof only in internal scripts; exploratory tasks disguised as strong.

---

## Automation / CI (Architect)

- **CI must run:** unit tests, integration tests, deterministic API-boundary tests (no live model / fragile internet dependency).
- **Artifacts:** capture raw request/response/DB evidence where required; live-path bundles outside CI if needed.
- **Not** manual-runbook-only as the sole proof model.

---

## Decay / caps

Developer proposes initial defaults (half-life or decay rule, max weight per signal, max cumulative penalty per project) with **rationale** in implementation notes or handoff; Architect reviews after implementation — **no pre-approval blocker** on constants.
