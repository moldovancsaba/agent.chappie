# Contract: Task / learning feedback v2 (app → worker)

## Purpose

Defines the **unified feedback and task-action envelope** for the first app (**3steps**, product name for the consultant follow-up surface). Learning from operator actions is core product behavior; `done` / `edited` / `declined` alone are no longer sufficient.

This contract is the **documented source of truth** for how the thin app forwards task-level actions to the **private Mac mini worker**. Implementation must match this shape consistently (Next.js API → worker).

## Relationship to Feedback v1

- [`feedback_v1.md`](feedback_v1.md) remains the historical platform envelope for job-level feedback in earlier examples.
- **Task learning and regeneration** use **v2** fields and `action_type` below. New work must not invent parallel ad-hoc payloads.

## Ownership

- produced by the App Layer (or app API proxy)
- accepted and executed by the private worker
- persisted in the **local worker brain** (SQLite), not as authoritative platform state in Neon

## Required concepts

- every task action maps to **exactly one** `action_type`
- optional `comment` refines regeneration (channel, segment, competitor, move type, specificity)
- worker uses stored rows (`task_feedback`, `generation_memory`, `replacement_history`, etc.) as defined in implementation

## Allowed `action_type` values

| `action_type` | Meaning |
| --- | --- |
| `done` | Task completed; remove from active set as appropriate; no negative teaching |
| `edit` | Operator adjusted wording; treat as **preference signal** for future similar tasks |
| `decline_and_replace` | Reject task; **replace immediately**; checklist stays **exactly 3** |
| `delete_only` | Remove from live set; **no** learning / no penalty |
| `delete_and_teach` | Remove and persist **what to avoid**; penalize similar future tasks (semantic, not string-only) |
| `hold_for_later` | Defer; remove from **active** checklist; preserve as deferred option |

## Recommended envelope shape (example)

```json
{
  "action_type": "decline_and_replace",
  "task_id": "task_abc123",
  "project_id": "client_acme_q2",
  "job_id": "job_optional",
  "comment": "make this about the pricing page",
  "submitted_at": "2026-03-25T12:00:00+00:00",
  "actor_id": "anonymous:session_xyz"
}
```

## Optional fields (extend as needed in code)

- `feedback_id`: unique id for this feedback event
- `app_id`: e.g. `app_consultant_followup`
- `linked_result_id` / `trace_run_id`: linkage back to a job result
- structured comment hints if the parser extracts them (channel, segment, competitor, move_type)

## Task output: `task_strength` (honest labeling)

Replacements and generated tasks must carry a **canonical** strength label so exploratory moves do not masquerade as strong actions.

Allowed values (enum):

- `strong_action`
- `tactical_action`
- `exploratory_action`

Rules:

- **UI** reflects this subtly (chip or metadata; no dramatic warning styling).
- **Exploratory** tasks are allowed; they must be **labeled**, not disguised as strong/tactical.

## Boundary rules

- the app does not run the triad or task generator; it forwards **this contract**
- the worker remains authoritative for regeneration, persistence, and ranking
- no leakage of internal observation payloads into the app beyond existing job result rules

## Formal implementation

- Python schemas and validation should live alongside other contracts in `src/agent_chappie/` when wired (e.g. `contract_schemas.py`, `validation.py`) and stay aligned with this document.

## Proof expectations (Phase 8)

- raw request JSON and raw response JSON for each major `action_type` path through **Next.js API**, not only internal scripts
- before/after task arrays; DB rows written; checklist remains exactly 3 where required
