from __future__ import annotations

import os
import sys
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.local_store import initialize_local_store, save_source_snapshot, upsert_knowledge_feedback
from agent_chappie.observation_engine import SourcePackage, build_source_hash
from agent_chappie.worker_bridge import WorkerBridgeConfig, build_workspace_payload, process_job_payload


class WorkerBridgeKnowledgeTests(unittest.TestCase):
    def test_workspace_payload_surfaces_knowledge_for_rich_source_without_actions(self) -> None:
        source = SourcePackage(
            project_id="project_knowledge",
            source_kind="uploaded_file",
            project_summary="managed_on_worker",
            raw_text=(
                "Competitive Analysis in the Marketing and SEO Intelligence Market with a Fortitude AI Focus. "
                "The document compares packaging, pricing bundles, trial offers, customer testimonials, "
                "and AI-led positioning across several vendors."
            ),
            source_ref="source_knowledge_001",
            file_name="competitive-analysis.docx",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source.__dict__, build_source_hash(source), db_path)

            workspace = build_workspace_payload(
                "project_knowledge",
                WorkerBridgeConfig(local_db_path=db_path),
            )

            self.assertTrue(workspace["knowledge_cards"])
            self.assertTrue(workspace["source_cards"])
            self.assertTrue(workspace["fact_chips"])
            self.assertTrue(workspace["draft_segments"])
            competitors = next(card for card in workspace["knowledge_cards"] if card["knowledge_id"] == "competitors_detected")
            self.assertTrue(any("Fortitude AI" in item for item in competitors["items"]))
            self.assertNotIn("Competitive", competitors["items"])
            self.assertNotIn("SEO", competitors["items"])
            self.assertNotIn("Several", competitors["items"])
            fact_labels = [fact["label"] for fact in workspace["fact_chips"]]
            self.assertTrue(any("Pricing bundles" in label or "packaging" in label.lower() for label in fact_labels))
            self.assertFalse(any(label in {"PDF", "Metadata", "Catalog", "Version", "Pages", "Type"} for label in fact_labels))
            self.assertTrue(workspace["source_cards"][0]["key_takeaway"])
            self.assertTrue(workspace["source_cards"][0]["business_impact"])
            self.assertIn("insight", competitors)
            self.assertIn("implication", competitors)
            self.assertIn("potential_moves", competitors)

    def test_workspace_payload_applies_knowledge_feedback_overlay(self) -> None:
        source = SourcePackage(
            project_id="project_knowledge_feedback",
            source_kind="manual_text",
            project_summary="managed_on_worker",
            raw_text="Fortitude AI uses pricing bundles, customer testimonials, and SEO positioning claims.",
            source_ref="source_feedback_001",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source.__dict__, build_source_hash(source), db_path)
            upsert_knowledge_feedback(
                project_id="project_knowledge_feedback",
                knowledge_id="market_summary",
                status="edited",
                corrected_title="Corrected Market Summary",
                corrected_summary="Edited summary from operator feedback.",
                corrected_items=["Custom knowledge item"],
                path=db_path,
            )

            workspace = build_workspace_payload(
                "project_knowledge_feedback",
                WorkerBridgeConfig(local_db_path=db_path),
            )

            market_card = next(card for card in workspace["knowledge_cards"] if card["knowledge_id"] == "market_summary")
            self.assertEqual(market_card["title"], "Corrected Market Summary")
            self.assertEqual(market_card["summary"], "Edited summary from operator feedback.")
            self.assertEqual(market_card["items"], ["Custom knowledge item"])
            self.assertEqual(market_card["annotation_status"], "edited")
            self.assertEqual(market_card["confidence_source"], "extracted")

    def test_process_job_payload_writes_tasks_from_draft_segments_for_rich_source(self) -> None:
        payload = {
            "job_request": {
                "job_id": "job_blocked_knowledge",
                "app_id": "consultant_followup_web",
                "project_id": "project_blocked_knowledge",
                "priority_class": "normal",
                "job_class": "light",
                "submitted_at": "2026-03-23T15:40:00+00:00",
                "requested_capability": "followup_task_recommendation",
                "input_payload": {
                    "context_type": "working_document",
                    "prompt": "Analyze the uploaded market document and return actions only if the evidence supports them.",
                    "artifacts": [{"type": "upload", "ref": "source_blocked_knowledge"}],
                },
                "source_refs": ["source_blocked_knowledge"],
            },
            "source_package": {
                "project_id": "project_blocked_knowledge",
                "source_kind": "manual_text",
                "project_summary": "managed_on_worker",
                "raw_text": (
                    "Competitive Analysis in the Marketing and SEO Intelligence Market with a Fortitude AI Focus. "
                    "The document compares packaging models, AI-led positioning, service-led onboarding, "
                    "customer testimonials, integration claims, trial offers, and buyer objections."
                ),
                "source_ref": "source_blocked_knowledge",
                "file_name": "competitive-analysis.docx",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            result = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))
            self.assertEqual(result["job_result"]["status"], "complete")
            self.assertTrue(result["job_result"]["result_payload"]["recommended_tasks"])

            workspace = build_workspace_payload(
                "project_blocked_knowledge",
                WorkerBridgeConfig(local_db_path=db_path),
            )
            self.assertTrue(workspace["knowledge_cards"])
            self.assertTrue(workspace["fact_chips"])
            self.assertTrue(workspace["draft_segments"])
            self.assertEqual(workspace["source_cards"][0]["status"], "processed")
            self.assertIn("competitive_snapshot", workspace)
            self.assertTrue(any(fact["category"] in {"pricing", "offer", "proof", "positioning"} for fact in workspace["fact_chips"]))
            top_task = result["job_result"]["result_payload"]["recommended_tasks"][0]
            self.assertIn("priority_label", top_task)
            self.assertIn("best_before", top_task)
            self.assertIn("is_next_best_action", top_task)


if __name__ == "__main__":
    unittest.main()
