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
    record_card_action,
    upsert_intelligence_cards,
)
from agent_chappie.worker_bridge import (
    WorkerBridgeConfig,
    apply_task_feedback,
    process_job_payload,
    process_management_request,
    regenerate_project_checklist,
    task_title_jaccard,
)


def setUpModule() -> None:
    for key in (
        "FLASHCARD_MLX_TRINITY",
        "FLASHCARD_MLX_TRIAD",
        "TRINITY_SUBPROCESS",
        "TRINITY_MAX_WALL_SECONDS",
        "TRINITY_PROGRESS_PERSIST",
    ):
        os.environ.pop(key, None)


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
            # Titles embed the same long source excerpt; Jaccard stays high when only move/evidence prefix changes.
            self.assertLess(
                task_title_jaccard(old_rank2_title, new_rank2["title"]),
                0.82,
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
                    0.92,
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


class IntelCardDeleteAndTeachMemoryTests(unittest.TestCase):
    def test_writes_avoid_title_and_parsed_comment_like_task_feedback(self) -> None:
        project_id = "project_intel_card_teach_mem"
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "brain.sqlite3")
            initialize_local_store(db_path)
            upsert_intelligence_cards(
                project_id,
                [
                    {
                        "card_id": "card_alpha",
                        "insight": "Competitor launched aggressive trial bundles for mid-market teams.",
                        "implication": "Your pipeline will face shorter evaluation cycles this quarter.",
                        "potential_moves": ["Shorten trial to 14 days with a guided checklist"],
                        "segment": "market",
                        "competitor": "RivalCo",
                        "channel": "web",
                        "fact_refs": [],
                        "source_refs": [],
                        "state": "active",
                    }
                ],
                [],
                path=db_path,
            )
            record_card_action(
                project_id,
                "card_alpha",
                "delete_and_teach",
                note="Focus on the pricing page; avoid email for this motion.",
                path=db_path,
            )
            rows = list_generation_memory_rows(project_id, path=db_path)
            kinds = {r["memory_kind"] for r in rows}
            self.assertIn("avoid_intel_card", kinds)
            self.assertIn("avoid_title", kinds)
            self.assertTrue(
                any(
                    str(r.get("memory_id") or "").startswith("avoid_title_intel::") for r in rows if r["memory_kind"] == "avoid_title"
                ),
                msg=f"expected avoid_title_intel memory_id, got {[r for r in rows if r['memory_kind']=='avoid_title']}",
            )
            self.assertTrue(any(r["memory_kind"] == "prefer_channel" for r in rows), msg="comment should parse prefer_channel")
            self.assertTrue(any(str(r.get("memory_id") or "").startswith("card_teach::") for r in rows))


if __name__ == "__main__":
    unittest.main()
