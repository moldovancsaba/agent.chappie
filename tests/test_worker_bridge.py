from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.local_store import (
    initialize_local_store,
    list_evidence_units,
    list_generation_memory_rows,
    list_task_feedback_rows,
    save_source_snapshot,
    upsert_knowledge_feedback,
)
from agent_chappie.observation_engine import SourcePackage, build_source_hash
from agent_chappie.worker_bridge import (
    WorkerBridgeConfig,
    build_auto_research_sources,
    build_workspace_payload,
    process_job_payload,
    process_task_feedback,
    select_task_support_bundle,
)


class WorkerBridgeKnowledgeTests(unittest.TestCase):
    def test_auto_research_rejects_irrelevant_public_results(self) -> None:
        source = SourcePackage(
            project_id="project_auto_research",
            source_kind="manual_text",
            project_summary="Marketing and SEO intelligence platform analysis",
            raw_text=(
                "Competitive Analysis in the Marketing and SEO Intelligence Market with a Fortitude AI Focus. "
                "The document compares onboarding friction, buyer proof, packaging, pricing, and trial offers."
            ),
            source_ref="source_auto_research",
            file_name="competitive-analysis.docx",
        )
        with mock.patch(
            "agent_chappie.worker_bridge.search_public_web_urls",
            return_value=[
                "https://oncodaily.com/oncolibrary/fortitude-101/",
                "https://fortitude.ai/pricing",
            ],
        ), mock.patch(
            "agent_chappie.worker_bridge.fetch_url_text",
            side_effect=[
                {
                    "title": "FORTITUDE-101 in gastric cancer",
                    "content": "Oncology gastric patient trial results and bemarituzumab treatment updates " * 10,
                },
                {
                    "title": "Fortitude AI pricing and onboarding",
                    "content": "Fortitude AI pricing onboarding trial testimonials SEO marketing analytics platform " * 10,
                },
            ],
        ):
            packages = build_auto_research_sources(source, [])

        self.assertEqual(len(packages), 1)
        self.assertIn("fortitude.ai/pricing", packages[0].raw_text)
        self.assertNotIn("oncodaily.com", packages[0].raw_text)

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
            self.assertGreaterEqual(competitors["support_count"], 1)
            fact_labels = [fact["label"] for fact in workspace["fact_chips"]]
            self.assertTrue(any("Pricing bundles" in label or "packaging" in label.lower() for label in fact_labels))
            self.assertFalse(any(label in {"PDF", "Metadata", "Catalog", "Version", "Pages", "Type"} for label in fact_labels))
            self.assertTrue(workspace["source_cards"][0]["key_takeaway"])
            self.assertTrue(workspace["source_cards"][0]["business_impact"])
            self.assertIn("insight", competitors)
            self.assertIn("implication", competitors)
            self.assertIn("potential_moves", competitors)
            self.assertTrue(next(card for card in workspace["knowledge_cards"] if card["knowledge_id"] == "market_summary")["support_count"] >= 1)
            source_ref = workspace["source_cards"][0]["source_ref"]
            card_refs = [card["knowledge_id"] for card in workspace["knowledge_cards"] if source_ref in card["source_refs"]]
            self.assertGreaterEqual(len(card_refs), 3)
            evidence_units = list_evidence_units("project_knowledge", path=db_path)
            self.assertTrue(evidence_units)

    def test_multiple_sources_can_strengthen_one_knowledge_card(self) -> None:
        source_a = SourcePackage(
            project_id="project_multi_source",
            source_kind="manual_text",
            project_summary="managed_on_worker",
            raw_text="Fortitude AI pricing bundles and onboarding friction are visible in the market.",
            source_ref="source_multi_a",
        )
        source_b = SourcePackage(
            project_id="project_multi_source",
            source_kind="manual_text",
            project_summary="managed_on_worker",
            raw_text="Another source confirms pricing pressure, onboarding comparison, and offer friction around Fortitude AI.",
            source_ref="source_multi_b",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source_a.__dict__, build_source_hash(source_a), db_path)
            save_source_snapshot(source_b.__dict__, build_source_hash(source_b), db_path)

            workspace = build_workspace_payload(
                "project_multi_source",
                WorkerBridgeConfig(local_db_path=db_path),
            )

            pricing_card = next(card for card in workspace["knowledge_cards"] if card["knowledge_id"] == "pricing_packaging")
            self.assertGreaterEqual(len(set(pricing_card["source_refs"])), 2)
            self.assertTrue(pricing_card["support_count"] >= 2)

    def test_task_support_bundle_filters_weaker_sources(self) -> None:
        evidence_units = [
            {
                "source_ref": "source_relevant",
                "unit_kind": "pricing",
                "label": "Fortitude AI pricing and onboarding pressure is visible.",
                "excerpt": "Fortitude AI pricing and onboarding pressure is visible in the source set.",
                "competitor": "Fortitude AI",
                "confidence": 0.82,
            },
            {
                "source_ref": "source_relevant",
                "unit_kind": "positioning",
                "label": "Fortitude AI is shaping comparison-stage buyer expectations.",
                "excerpt": "Fortitude AI is shaping comparison-stage buyer expectations.",
                "competitor": "Fortitude AI",
                "confidence": 0.77,
            },
            {
                "source_ref": "source_weak",
                "unit_kind": "proof",
                "label": "Generic customer story with no pricing overlap.",
                "excerpt": "Generic customer story with no pricing overlap.",
                "competitor": "",
                "confidence": 0.35,
            },
        ]

        source_refs, excerpt = select_task_support_bundle(
            segment_text="Fortitude AI pricing and onboarding pressure is visible.",
            segment_source_refs=["source_relevant", "source_weak"],
            evidence_units=evidence_units,
            competitor="Fortitude AI",
            move_bucket="pricing_or_offer_move",
        )

        self.assertEqual(source_refs, ["source_relevant"])
        self.assertIn("Fortitude AI", excerpt or "")

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
            self.assertIn("confidence_class", top_task)
            self.assertIn("target_channel", top_task)
            self.assertIn("target_segment", top_task)
            self.assertIn("mechanism", top_task)
            self.assertIn("done_definition", top_task)
            self.assertIn("execution_steps", top_task)
            self.assertEqual(len(top_task["execution_steps"]), 4)
            self.assertIn("supporting_signal_refs", top_task)
            self.assertIn("supporting_segment_ids", top_task)
            self.assertIn("supporting_source_refs", top_task)
            task_types = [task["task_type"] for task in result["job_result"]["result_payload"]["recommended_tasks"]]
            self.assertLessEqual(task_types.count("information_request"), 1)
            self.assertGreaterEqual(sum(task_type != "information_request" for task_type in task_types), 2)
            move_buckets = [task["move_bucket"] for task in result["job_result"]["result_payload"]["recommended_tasks"]]
            self.assertGreaterEqual(len(set(move_buckets)), 2)
            titles = [task["title"] for task in result["job_result"]["result_payload"]["recommended_tasks"]]
            self.assertFalse(any("buyer-facing response" in title.lower() for title in titles))
            self.assertTrue(any("pricing page" in title.lower() or "homepage" in title.lower() or "enrollment" in title.lower() for title in titles))
            self.assertFalse(any("current competitor frame" in title.lower() for title in titles))
            self.assertFalse(any("drafted a buyer-pressure segment" in task["why_now"].lower() for task in result["job_result"]["result_payload"]["recommended_tasks"]))

    def test_task_feedback_regenerates_three_tasks(self) -> None:
        payload = {
            "job_request": {
                "job_id": "job_feedback_regen",
                "app_id": "consultant_followup_web",
                "project_id": "project_feedback_regen",
                "priority_class": "normal",
                "job_class": "light",
                "submitted_at": "2026-03-23T15:40:00+00:00",
                "requested_capability": "followup_task_recommendation",
                "input_payload": {
                    "context_type": "working_document",
                    "prompt": "Analyze the uploaded market document and return actions.",
                    "artifacts": [{"type": "upload", "ref": "source_feedback_regen"}],
                },
                "source_refs": ["source_feedback_regen"],
            },
            "source_package": {
                "project_id": "project_feedback_regen",
                "source_kind": "manual_text",
                "project_summary": "managed_on_worker",
                "raw_text": (
                    "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, "
                    "trial offers, customer testimonials, integration claims, and onboarding friction."
                ),
                "source_ref": "source_feedback_regen",
                "file_name": "feedback-analysis.docx",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            first = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))
            first_tasks = first["job_result"]["result_payload"]["recommended_tasks"]
            feedback_response = process_task_feedback(
                "project_feedback_regen",
                {
                    "job_id": "job_feedback_regen",
                    "task_feedback_items": [
                        {
                            "feedback_id": "task_feedback_1",
                            "rank": 1,
                            "original_title": first_tasks[0]["title"],
                            "original_expected_advantage": first_tasks[0]["expected_advantage"],
                            "feedback_type": "declined",
                            "feedback_comment": "Too generic.",
                        }
                    ],
                },
                WorkerBridgeConfig(local_db_path=db_path),
            )
            regenerated = feedback_response["job_result"]["result_payload"]["recommended_tasks"]
            self.assertEqual(len(regenerated), 3)
            self.assertNotEqual(regenerated[0]["title"], first_tasks[0]["title"])
            stored_feedback = list_task_feedback_rows("project_feedback_regen", path=db_path)
            self.assertEqual(stored_feedback[0]["feedback_comment"], "Too generic.")
            memory_rows = list_generation_memory_rows("project_feedback_regen", path=db_path)
            self.assertTrue(any(row["memory_kind"] == "avoid_title" for row in memory_rows))

    def test_commented_task_persists_memory_and_changes_regeneration(self) -> None:
        payload = {
            "job_request": {
                "job_id": "job_feedback_comment",
                "app_id": "consultant_followup_web",
                "project_id": "project_feedback_comment",
                "priority_class": "normal",
                "job_class": "light",
                "submitted_at": "2026-03-23T15:40:00+00:00",
                "requested_capability": "followup_task_recommendation",
                "input_payload": {
                    "context_type": "working_document",
                    "prompt": "Analyze the uploaded market document and return actions.",
                    "artifacts": [{"type": "upload", "ref": "source_feedback_comment"}],
                },
                "source_refs": ["source_feedback_comment"],
            },
            "source_package": {
                "project_id": "project_feedback_comment",
                "source_kind": "manual_text",
                "project_summary": "managed_on_worker",
                "raw_text": (
                    "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, "
                    "trial offers, customer testimonials, integration claims, and onboarding friction."
                ),
                "source_ref": "source_feedback_comment",
                "file_name": "feedback-analysis.docx",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            first = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))
            first_tasks = first["job_result"]["result_payload"]["recommended_tasks"]
            response = process_task_feedback(
                "project_feedback_comment",
                {
                    "job_id": "job_feedback_comment",
                    "task_feedback_items": [
                        {
                            "feedback_id": "task_feedback_comment_1",
                            "rank": 3,
                            "original_title": first_tasks[2]["title"],
                            "original_expected_advantage": first_tasks[2]["expected_advantage"],
                            "feedback_type": "commented",
                            "feedback_comment": "Too generic and overlapping with the homepage messaging task.",
                        }
                    ],
                },
                WorkerBridgeConfig(local_db_path=db_path),
            )
            regenerated = response["job_result"]["result_payload"]["recommended_tasks"]
            self.assertEqual(len(regenerated), 3)
            self.assertNotIn(first_tasks[2]["title"], [task["title"] for task in regenerated])
            memory_rows = list_generation_memory_rows("project_feedback_comment", path=db_path)
            self.assertTrue(any(row["memory_kind"] == "avoid_bucket" for row in memory_rows))

    def test_edited_task_creates_preference_memory(self) -> None:
        payload = {
            "job_request": {
                "job_id": "job_feedback_edit",
                "app_id": "consultant_followup_web",
                "project_id": "project_feedback_edit",
                "priority_class": "normal",
                "job_class": "light",
                "submitted_at": "2026-03-23T15:40:00+00:00",
                "requested_capability": "followup_task_recommendation",
                "input_payload": {
                    "context_type": "working_document",
                    "prompt": "Analyze the uploaded market document and return actions.",
                    "artifacts": [{"type": "upload", "ref": "source_feedback_edit"}],
                },
                "source_refs": ["source_feedback_edit"],
            },
            "source_package": {
                "project_id": "project_feedback_edit",
                "source_kind": "manual_text",
                "project_summary": "managed_on_worker",
                "raw_text": (
                    "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, "
                    "trial offers, customer testimonials, integration claims, and onboarding friction."
                ),
                "source_ref": "source_feedback_edit",
                "file_name": "feedback-analysis.docx",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            first = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))
            response = process_task_feedback(
                "project_feedback_edit",
                {
                    "job_id": "job_feedback_edit",
                    "task_feedback_items": [
                        {
                            "feedback_id": "task_feedback_edit_1",
                            "rank": 2,
                            "original_title": first["job_result"]["result_payload"]["recommended_tasks"][1]["title"],
                            "original_expected_advantage": first["job_result"]["result_payload"]["recommended_tasks"][1]["expected_advantage"],
                            "feedback_type": "edited",
                            "adjusted_text": "Rewrite the pricing page hero this week to answer the strongest proof and trial pressure before buyers default to Fortitude AI",
                            "feedback_comment": "Use the pricing page, not the homepage comparison section.",
                        }
                    ],
                },
                WorkerBridgeConfig(local_db_path=db_path),
            )
            regenerated_titles = [task["title"] for task in response["job_result"]["result_payload"]["recommended_tasks"]]
            self.assertIn("Rewrite the pricing page hero this week to answer the strongest proof and trial pressure before buyers default to Fortitude AI", regenerated_titles)
            memory_rows = list_generation_memory_rows("project_feedback_edit", path=db_path)
            self.assertTrue(any(row["memory_kind"] == "prefer_channel" for row in memory_rows))

    def test_process_job_payload_can_reuse_same_segment_templates_across_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)

            for project_id, job_id, source_ref in (
                ("project_alpha", "job_alpha", "source_alpha"),
                ("project_beta", "job_beta", "source_beta"),
            ):
                payload = {
                    "job_request": {
                        "job_id": job_id,
                        "app_id": "consultant_followup_web",
                        "project_id": project_id,
                        "priority_class": "normal",
                        "job_class": "light",
                        "submitted_at": "2026-03-24T07:00:00+00:00",
                        "requested_capability": "followup_task_recommendation",
                        "input_payload": {
                            "context_type": "working_document",
                            "prompt": "Identify competitive signals and return exactly 3 actionable follow-up tasks.",
                            "artifacts": [{"type": "upload", "ref": source_ref}],
                        },
                    },
                    "source_package": {
                        "project_id": project_id,
                        "source_kind": "manual_text",
                        "project_summary": "managed_on_worker",
                        "raw_text": (
                            "Competitive Analysis in the Marketing and SEO Intelligence Market with a Fortitude AI Focus. "
                            "The document compares packaging models, AI-led positioning, service-led onboarding, "
                            "customer testimonials, integration claims, trial offers, and buyer objections."
                        ),
                        "source_ref": source_ref,
                    },
                }
                result = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))
                self.assertEqual(result["job_result"]["status"], "complete")
                self.assertEqual(len(result["job_result"]["result_payload"]["recommended_tasks"]), 3)

    def test_judge_prefers_distinct_move_buckets(self) -> None:
        payload = {
            "job_request": {
                "job_id": "job_diverse_buckets",
                "app_id": "consultant_followup_web",
                "project_id": "project_diverse_buckets",
                "priority_class": "normal",
                "job_class": "light",
                "submitted_at": "2026-03-24T07:00:00+00:00",
                "requested_capability": "followup_task_recommendation",
                "input_payload": {
                    "context_type": "working_document",
                    "prompt": "Identify competitive signals and return exactly 3 actionable follow-up tasks.",
                    "artifacts": [{"type": "upload", "ref": "source_diverse_buckets"}],
                },
            },
            "source_package": {
                "project_id": "project_diverse_buckets",
                "source_kind": "manual_text",
                "project_summary": "managed_on_worker",
                "raw_text": (
                    "FlowOps raised onboarding and pricing friction in the SEO market. "
                    "Competitors are using testimonials, proof blocks, integration claims, and comparison messaging. "
                    "One exposed operator is reducing staff and may sell assets. "
                    "Trial-led acquisition pressure is rising."
                ),
                "source_ref": "source_diverse_buckets",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            result = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))
            tasks = result["job_result"]["result_payload"]["recommended_tasks"]
            move_buckets = [task["move_bucket"] for task in tasks]
            self.assertEqual(len(tasks), 3)
            self.assertGreaterEqual(len(set(move_buckets)), 3)
            self.assertEqual(tasks[0]["priority_label"], "critical")
            self.assertTrue(any("this week" in task["title"].lower() for task in tasks))


if __name__ == "__main__":
    unittest.main()
