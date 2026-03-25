# Phase 8 — feedback_v2 proof artifact (v1)

**Scope:** Worker path `POST /projects/{project_id}/tasks/feedback` (management API) and persistence. Next.js path `POST /api/tasks/feedback` forwards the same JSON body to the worker and returns `{ "tasks": [ …3… ] }`.

**Automated proof:** `tests/test_feedback_api.py` (run with `PYTHONPATH=src python3 -m unittest tests.test_feedback_api -v` from repo root with `.venv` activated).

---

## 1. Example: decline_and_replace + comment (worker-equivalent request)

Captured from a deterministic local run (`process_management_request` + temp SQLite, 2026-03-25).

### Raw request JSON

```json
{
  "project_id": "project_proof_doc",
  "task_id": "2",
  "action_type": "decline_and_replace",
  "comment": "need trust move"
}
```

### Before / after task titles (3 each)

**Before**

1. Add pricing comparison block on pricing page this week before Fortitude AI's onboarding friction sets expectations for buyers  
2. Rewrite homepage comparison copy this week to answer the visible competitor trial before buyers default to it  
3. Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using pricing comparison first  

**After**

1. Add pricing comparison block on pricing page this week before Fortitude AI's onboarding friction sets expectations for buyers  
2. Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using pricing comparison first  
3. Request one sharper source this week that resolves the strongest Market Summary gap before the next buyer decision window  

### `task_feedback` row (sample)

```json
{
  "feedback_id": "fb_v2_project_proof_doc_1774436402578",
  "task_id": "2",
  "job_id": "job1",
  "project_id": "project_proof_doc",
  "original_title": "Rewrite homepage comparison copy this week to answer the visible competitor trial before buyers default to it",
  "feedback_type": "declined",
  "feedback_comment": "need trust move",
  "action_type": "decline_and_replace",
  "replacement_generated": 1
}
```

### `generation_memory` rows (sample)

- `avoid_title` on normalized declined title (semantic suppression)  
- `prefer_bucket` → `proof_or_trust_move` from comment parser (`need trust move`)

```json
[
  {
    "memory_kind": "avoid_title",
    "pattern_key": "rewrite homepage comparison copy this week to answer the visible competitor trial before buyers default to it",
    "weight": 3.0
  },
  {
    "memory_kind": "prefer_bucket",
    "pattern_key": "proof_or_trust_move",
    "signal_value": "proof_or_trust_move",
    "weight": 5.0
  }
]
```

---

## 2. App boundary (Next.js)

- **Route:** `POST /api/tasks/feedback`  
- **Body:** same fields as request above (`project_id`, `task_id`, `action_type`, optional `comment`, optional `edited_title` for `edit`).  
- **Response:** `{ "tasks": [ …exactly 3… ] }` when `AGENT_BRIDGE_MODE=worker` and the worker returns three tasks.  
- **Full live capture** (curl against `localhost:3000` + running worker) can be appended in a follow-up revision; CI relies on Python tests for determinism.

---

## 3. Implementation pointers

| Piece | Location |
| --- | --- |
| `apply_task_feedback` | `src/agent_chappie/worker_bridge.py` |
| HTTP route | `POST .../projects/{id}/tasks/feedback` in same module |
| Active checklist persistence | `project_active_checklist` in `src/agent_chappie/local_store.py` |
| `action_type` column | `task_feedback.action_type` (migration via `_ensure_column`) |
| Next API | `apps/consultant-followup-web/app/api/tasks/feedback/route.ts` |
| Client helper | `submitWorkerTaskFeedbackV2` in `apps/consultant-followup-web/lib/worker-bridge.ts` |

---

## 4. Follow-up (M5 hardening)

- Append **raw** Next.js request/response once a single scripted run is captured against dev servers.  
- Keep **Python tests** as the non-flaky CI gate; do not depend on live model output in CI.
