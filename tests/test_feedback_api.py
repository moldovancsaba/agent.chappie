"""
Deterministic Phase 8 tests: feedback_v2 through the same routing as POST /projects/{id}/tasks/feedback.
No UI, no live model variance (fixed source text + local SQLite).
"""

from __future__ import annotations

import os
import tempfile
import unittest

from agent_chappie.local_store import (
    initialize_local_store,
    list_generation_memory_rows,
    list_task_feedback_rows,
)
from agent_chappie.worker_bridge import (
    WorkerBridgeConfig,
    apply_task_feedback,
    process_job_payload,
    process_management_request,
    regenerate_project_checklist,
    task_title_jaccard,
)


def _fortitude_job_payload(project_id: str, job_id: str, source_ref: str) -> dict:
    return {
        "job_request": {
            "job_id": job_id,
            "app_id": "consultant_followup_web",
            "project_id": project_id,
            "priority_class": "normal",
            "job_class": "light",
            "submitted_at": "2026-03-25T10:00:00+00:00",
            "requested_capability": "followup_task_recommendation",
            "input_payload": {
                "context_type": "working_document",
                "prompt": "Analyze the uploaded market document and return actions.",
                "artifacts": [{"type": "upload", "ref": source_ref}],
            },
            "source_refs": [source_ref],
        },
        "source_package": {
            "project_id": project_id,
            "source_kind": "manual_text",
            "project_summary": "managed_on_worker",
            "raw_text": (
                "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, "
                "trial offers, customer testimonials, integration claims, and onboarding friction."
            ),
            "source_ref": source_ref,
            "file_name": "feedback-analysis.docx",
        },
    }


def _post_tasks_feedback_v2(project_id: str, body: dict, config: WorkerBridgeConfig) -> dict:
    response, status = process_management_request(
        "POST",
        f"/projects/{project_id}/tasks/feedback",
        body,
        config,
    )
    if status != 200:
        raise AssertionError(f"expected 200, got {status}: {response}")
    return response


class FeedbackV2ApiTests(unittest.TestCase):
    def test_case_decline_and_replace_three_tasks_low_similarity(self) -> None:
        project_id = "project_api_decline_v2"
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "brain.sqlite3")
            initialize_local_store(db_path)
            cfg = WorkerBridgeConfig(local_db_path=db_path)
            first = process_job_payload(
                _fortitude_job_payload(project_id, "job_api_decline", "src_api_decline"),
                cfg,
            )
            before = first["job_result"]["result_payload"]["recommended_tasks"]
            self.assertEqual(len(before), 3)
            old_rank2_title = before[1]["title"]

            resp = _post_tasks_feedback_v2(
                project_id,
                {
                    "project_id": project_id,
                    "task_id": "2",
                    "action_type": "decline_and_replace",
                    "comment": "Too generic for this week.",
                },
                cfg,
            )
            tasks = resp["tasks"]
            self.assertEqual(len(tasks), 3)
            new_rank2 = tasks[1]
            self.assertLess(
                task_title_jaccard(old_rank2_title, new_rank2["title"]),
                0.6,
                msg=f"replacement too similar: {old_rank2_title!r} vs {new_rank2['title']!r}",
            )
            rows = list_task_feedback_rows(project_id, path=db_path)
            self.assertEqual(rows[0].get("action_type"), "decline_and_replace")

    def test_case_delete_and_teach_suppresses_similar_regeneration(self) -> None:
        project_id = "project_api_teach_v2"
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "brain.sqlite3")
            initialize_local_store(db_path)
            cfg = WorkerBridgeConfig(local_db_path=db_path)
            seeded = process_job_payload(
                _fortitude_job_payload(project_id, "job_api_teach", "src_api_teach"),
                cfg,
            )
            taught_title = seeded["job_result"]["result_payload"]["recommended_tasks"][0]["title"]
            stored = apply_task_feedback(
                {
                    "project_id": project_id,
                    "task_id": "1",
                    "action_type": "delete_and_teach",
                    "comment": "Never recommend this homepage comparison block pattern again.",
                },
                cfg,
            )
            self.assertEqual(len(stored["tasks"]), 3)
            # Full regen without retaining tasks — avoid_title memory should suppress near-duplicates of the taught title.
            regen = regenerate_project_checklist(
                project_id,
                cfg,
                job_id="job_full_regen_after_teach",
                app_id="consultant_followup_web",
                retained_tasks=None,
            )
            for t in regen["result_payload"]["recommended_tasks"]:
                self.assertLessEqual(
                    task_title_jaccard(t["title"], taught_title),
                    0.65,
                    msg=f"similar pattern reappeared: {t['title']!r} vs taught {taught_title!r}",
                )
            mem = list_generation_memory_rows(project_id, path=db_path)
            self.assertTrue(any(m["memory_kind"] == "avoid_title" for m in mem))

    def test_case_comment_trust_move_shifts_bucket(self) -> None:
        project_id = "project_api_trust_v2"
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "brain.sqlite3")
            initialize_local_store(db_path)
            cfg = WorkerBridgeConfig(local_db_path=db_path)
            process_job_payload(
                _fortitude_job_payload(project_id, "job_api_trust", "src_api_trust"),
                cfg,
            )
            resp = _post_tasks_feedback_v2(
                project_id,
                {
                    "project_id": project_id,
                    "task_id": "2",
                    "action_type": "decline_and_replace",
                    "comment": "need trust move",
                },
                cfg,
            )
            tasks = resp["tasks"]
            self.assertEqual(len(tasks), 3)
            buckets = {t.get("move_bucket") for t in tasks}
            self.assertIn(
                "proof_or_trust_move",
                buckets,
                msg=f"expected at least one proof/trust bucket, got {buckets}",
            )
            gm = list_generation_memory_rows(project_id, path=db_path)
            self.assertTrue(
                any(r.get("memory_kind") == "prefer_bucket" and r.get("pattern_key") == "proof_or_trust_move" for r in gm),
                msg=f"generation_memory missing prefer_bucket proof: {gm[:5]}",
            )

    def test_management_route_returns_tasks_shape(self) -> None:
        project_id = "project_api_route_shape"
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "brain.sqlite3")
            initialize_local_store(db_path)
            cfg = WorkerBridgeConfig(local_db_path=db_path)
            process_job_payload(
                _fortitude_job_payload(project_id, "job_shape", "src_shape"),
                cfg,
            )
            out = _post_tasks_feedback_v2(
                project_id,
                {
                    "project_id": project_id,
                    "task_id": "1",
                    "action_type": "hold_for_later",
                    "comment": "later",
                },
                cfg,
            )
            self.assertIn("tasks", out)
            self.assertEqual(len(out["tasks"]), 3)


if __name__ == "__main__":
    unittest.main()
