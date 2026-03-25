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
    list_draft_segments,
    list_evidence_units,
    list_generation_memory_rows,
    list_task_feedback_rows,
    save_source_snapshot,
    upsert_draft_segment_feedback,
    upsert_knowledge_feedback,
)
from agent_chappie.observation_engine import SourcePackage, build_source_hash, clean_entity, extract_action_detail
from agent_chappie.worker_bridge import (
    WorkerBridgeConfig,
    build_auto_research_sources,
    build_workspace_payload,
    process_job_payload,
    process_task_feedback,
    select_task_support_bundle,
)


class WorkerBridgeKnowledgeTests(unittest.TestCase):
    def test_clean_entity_rejects_imperative_verbs(self) -> None:
        self.assertIsNone(clean_entity("Add"))
        self.assertIsNone(clean_entity("Rewrite"))
        self.assertIsNone(clean_entity("Publish"))
        self.assertIsNone(clean_entity("FAQ"))
        self.assertIsNone(clean_entity("Notes"))
        self.assertIsNone(clean_entity("Its"))
        self.assertIsNone(clean_entity("Trial"))
        self.assertEqual(clean_entity("Fortitude AI Focus"), "Fortitude AI")

    def test_extract_action_detail_captures_channel_section_asset_and_claim(self) -> None:
        detail = extract_action_detail(
            "Add a pricing comparison block and onboarding FAQ to the pricing page this week before Fortitude AI's free trial sets buyer expectations."
        )

        self.assertEqual(detail["channel"], "pricing page")
        self.assertEqual(detail["section"], "onboarding FAQ")
        self.assertEqual(detail["asset"], "pricing comparison block")
        self.assertEqual(detail["claim"], "free trial")

    def test_workspace_builds_asset_aware_draft_segments_from_one_source(self) -> None:
        source = SourcePackage(
            project_id="project_asset_segments",
            source_kind="manual_text",
            project_summary="managed_on_worker",
            raw_text=(
                "Add a pricing comparison block and onboarding FAQ to the pricing page this week before Fortitude AI's free trial sets buyer expectations. "
                "Rewrite the homepage hero section to answer the no engineering required claim before comparison-stage buyers default to Fortitude AI."
            ),
            source_ref="source_asset_segments",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source.__dict__, build_source_hash(source), db_path)

            workspace = build_workspace_payload(
                "project_asset_segments",
                WorkerBridgeConfig(local_db_path=db_path),
            )

            segment_titles = [segment["title"].lower() for segment in workspace["draft_segments"]]
            self.assertTrue(any("pricing comparison block" in title for title in segment_titles))
            self.assertTrue(any("hero section" in title or "homepage comparison section" in title for title in segment_titles))

    def test_knowledge_cards_prefer_action_aware_unit_items(self) -> None:
        source = SourcePackage(
            project_id="project_action_cards",
            source_kind="manual_text",
            project_summary="managed_on_worker",
            raw_text=(
                "Add a pricing comparison block and onboarding FAQ to the pricing page this week before Fortitude AI's free trial sets buyer expectations. "
                "Rewrite the homepage hero section to answer the no engineering required claim before comparison-stage buyers default to Fortitude AI."
            ),
            source_ref="source_action_cards",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source.__dict__, build_source_hash(source), db_path)

            workspace = build_workspace_payload(
                "project_action_cards",
                WorkerBridgeConfig(local_db_path=db_path),
            )

            pricing_card = next(card for card in workspace["knowledge_cards"] if card["knowledge_id"] == "pricing_packaging")
            positioning_card = next(card for card in workspace["knowledge_cards"] if card["knowledge_id"] == "offer_positioning")
            self.assertTrue(any("pricing comparison block" in item.lower() for item in pricing_card["items"]))
            self.assertTrue(any("hero section" in item.lower() or "homepage comparison section" in item.lower() for item in positioning_card["items"]))

    def test_knowledge_cards_reduce_cross_card_item_duplication(self) -> None:
        source = SourcePackage(
            project_id="project_card_dedup",
            source_kind="manual_text",
            project_summary="managed_on_worker",
            raw_text=(
                "Add a pricing comparison block and onboarding FAQ to the pricing page this week before Fortitude AI's free trial sets buyer expectations. "
                "Add proof blocks to the homepage hero section to answer the no engineering required claim before buyers already comparing options default to Fortitude AI."
            ),
            source_ref="source_card_dedup",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source.__dict__, build_source_hash(source), db_path)

            workspace = build_workspace_payload(
                "project_card_dedup",
                WorkerBridgeConfig(local_db_path=db_path),
            )

            cards = {card["knowledge_id"]: card for card in workspace["knowledge_cards"]}
            market_items = {item.lower() for item in cards["market_summary"]["items"]}
            pricing_items = {item.lower() for item in cards["pricing_packaging"]["items"]}
            positioning_items = {item.lower() for item in cards["offer_positioning"]["items"]}
            proof_items = {item.lower() for item in cards["proof_signals"]["items"]}

            self.assertTrue(market_items)
            self.assertTrue(pricing_items or positioning_items or proof_items)
            self.assertTrue(market_items.isdisjoint(pricing_items))
            self.assertTrue(market_items.isdisjoint(positioning_items))
            self.assertTrue(market_items.isdisjoint(proof_items))

    def test_source_cards_and_snapshot_use_action_aware_clusters(self) -> None:
        source = SourcePackage(
            project_id="project_source_snapshot_clusters",
            source_kind="manual_text",
            project_summary="managed_on_worker",
            raw_text=(
                "Add a pricing comparison block and onboarding FAQ to the pricing page this week before Fortitude AI's free trial sets buyer expectations. "
                "Rewrite the homepage hero section to answer the no engineering required claim before buyers already comparing options default to Fortitude AI."
            ),
            source_ref="source_source_snapshot_clusters",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source.__dict__, build_source_hash(source), db_path)

            workspace = build_workspace_payload(
                "project_source_snapshot_clusters",
                WorkerBridgeConfig(local_db_path=db_path),
            )

            source_card = workspace["source_cards"][0]
            snapshot = workspace["competitive_snapshot"]
            combined_source = f"{source_card['key_takeaway']} {source_card['business_impact']}".lower()
            combined_snapshot = " ".join(
                [
                    snapshot["pricing_position"],
                    snapshot["acquisition_strategy_comparison"],
                    snapshot["current_weakness"],
                    *snapshot["active_threats"],
                ]
            ).lower()

            self.assertIn("fortitude ai", combined_source)
            self.assertTrue("pricing page" in combined_source or "homepage" in combined_source)
            self.assertTrue("free trial" in combined_source or "no engineering required" in combined_source)
            self.assertIn("fortitude ai", combined_snapshot)
            self.assertTrue("pricing page" in combined_snapshot or "homepage" in combined_snapshot)
            self.assertTrue("free trial" in combined_snapshot or "no engineering required" in combined_snapshot)

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
            self.assertTrue(any(unit.get("channel") for unit in evidence_units))

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

        source_bundle, excerpt = select_task_support_bundle(
            segment_text="Fortitude AI pricing and onboarding pressure is visible.",
            segment_source_refs=["source_relevant", "source_weak"],
            evidence_units=evidence_units,
            competitor="Fortitude AI",
            move_bucket="pricing_or_offer_move",
        )

        self.assertEqual([item["source_ref"] for item in source_bundle], ["source_relevant"])
        self.assertGreaterEqual(source_bundle[0]["relevance_score"], 1.0)
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

    def test_workspace_hides_deleted_knowledge_and_parks_held_knowledge(self) -> None:
        source = SourcePackage(
            project_id="project_knowledge_delete_modes",
            source_kind="manual_text",
            project_summary="managed_on_worker",
            raw_text="Fortitude AI uses pricing bundles, customer testimonials, and SEO positioning claims.",
            source_ref="source_delete_modes",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source.__dict__, build_source_hash(source), db_path)
            upsert_knowledge_feedback(
                project_id="project_knowledge_delete_modes",
                knowledge_id="market_summary",
                status="deleted_silent",
                original_payload={"title": "Market Summary", "summary": "Delete me"},
                path=db_path,
            )
            upsert_knowledge_feedback(
                project_id="project_knowledge_delete_modes",
                knowledge_id="proof_signals",
                status="held_for_later",
                original_payload={"title": "Proof Signals", "summary": "Park this card."},
                path=db_path,
            )

            workspace = build_workspace_payload(
                "project_knowledge_delete_modes",
                WorkerBridgeConfig(local_db_path=db_path),
            )

            knowledge_ids = [card["knowledge_id"] for card in workspace["knowledge_cards"]]
            self.assertNotIn("market_summary", knowledge_ids)
            self.assertNotIn("proof_signals", knowledge_ids)
            held_segments = [segment for segment in workspace["draft_segments"] if segment["segment_kind"] == "held_knowledge"]
            self.assertTrue(any(segment["title"] == "Proof Signals" for segment in held_segments))

    def test_workspace_hides_deleted_draft_segment(self) -> None:
        source = SourcePackage(
            project_id="project_draft_segment_delete",
            source_kind="manual_text",
            project_summary="managed_on_worker",
            raw_text="Fortitude AI uses pricing bundles, customer testimonials, and SEO positioning claims.",
            source_ref="source_draft_segment_delete",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source.__dict__, build_source_hash(source), db_path)
            initial_segments = list_draft_segments("project_draft_segment_delete", path=db_path)
            if not initial_segments:
                workspace = build_workspace_payload(
                    "project_draft_segment_delete",
                    WorkerBridgeConfig(local_db_path=db_path),
                )
                initial_segments = workspace["draft_segments"]
            self.assertTrue(initial_segments)
            upsert_draft_segment_feedback(
                project_id="project_draft_segment_delete",
                segment_id=initial_segments[0]["segment_id"],
                status="deleted_silent",
                original_payload={"title": initial_segments[0]["title"]},
                path=db_path,
            )
            workspace = build_workspace_payload(
                "project_draft_segment_delete",
                WorkerBridgeConfig(local_db_path=db_path),
            )
            visible_ids = {segment["segment_id"] for segment in workspace["draft_segments"]}
            self.assertNotIn(initial_segments[0]["segment_id"], visible_ids)

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
            self.assertTrue(any("Fortitude" in step for step in top_task["execution_steps"]))
            self.assertTrue(any("pricing comparison block" in step.lower() or "homepage comparison section" in step.lower() for step in top_task["execution_steps"]))
            self.assertTrue(any(token in top_task["done_definition"].lower() for token in ("pricing comparison block", "homepage comparison section", "proof block")))
            self.assertTrue(any(token in top_task["execution_steps"][0].lower() for token in ("claim", "free trial", "onboarding", "pricing")))
            self.assertIn("supporting_signal_refs", top_task)
            self.assertIn("supporting_segment_ids", top_task)
            self.assertIn("supporting_signal_scores", top_task)
            self.assertIn("supporting_segment_scores", top_task)
            self.assertIn("supporting_source_refs", top_task)
            self.assertIn("supporting_source_scores", top_task)
            self.assertTrue(top_task["supporting_source_scores"])
            self.assertIn("relevance_score", top_task["supporting_source_scores"][0])
            self.assertTrue(top_task["supporting_signal_scores"])
            self.assertIn("relevance_score", top_task["supporting_signal_scores"][0])
            self.assertTrue(top_task["supporting_segment_scores"])
            self.assertIn("relevance_score", top_task["supporting_segment_scores"][0])
            self.assertIn("Fortitude", top_task["why_now"])
            self.assertTrue(any(token in top_task["why_now"].lower() for token in ("pricing", "offer", "proof", "signal")))
            self.assertIn("Fortitude", top_task["title"])
            self.assertTrue(any(token in top_task["title"].lower() for token in ("pricing page", "homepage", "comparison", "proof", "contact")))
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

    def test_process_job_payload_uses_explicit_claim_and_asset_in_task_text(self) -> None:
        payload = {
            "job_request": {
                "job_id": "job_explicit_claim_asset",
                "app_id": "consultant_followup_web",
                "project_id": "project_explicit_claim_asset",
                "priority_class": "normal",
                "job_class": "light",
                "submitted_at": "2026-03-24T10:00:00+00:00",
                "requested_capability": "followup_task_recommendation",
                "input_payload": {
                    "context_type": "working_document",
                    "prompt": "Analyze the uploaded market document and return the next three actions.",
                    "artifacts": [{"type": "upload", "ref": "source_explicit_claim_asset"}],
                },
                "source_refs": ["source_explicit_claim_asset"],
            },
            "source_package": {
                "project_id": "project_explicit_claim_asset",
                "source_kind": "manual_text",
                "project_summary": "managed_on_worker",
                "raw_text": (
                    "Add a pricing comparison block and onboarding FAQ to the pricing page this week before Fortitude AI's free trial sets buyer expectations. "
                    "Rewrite the homepage hero section to answer the no engineering required claim before buyers already comparing options default to Fortitude AI."
                ),
                "source_ref": "source_explicit_claim_asset",
                "file_name": "competitive-analysis.docx",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            result = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))

            tasks = result["job_result"]["result_payload"]["recommended_tasks"]
            combined = " ".join(
                [
                    task["title"] + " " + task["why_now"] + " " + task["expected_advantage"]
                    for task in tasks
                ]
            ).lower()

            self.assertIn("fortitude ai", combined)
            self.assertTrue("free trial" in combined or "no engineering required" in combined)
            self.assertTrue("pricing page" in combined or "homepage hero section" in combined)
            self.assertNotIn("current competitor frame", combined)
            self.assertNotIn("comparison-stage buyers", combined)
            self.assertNotEqual(tasks[2]["task_type"], "information_request")
            self.assertFalse(any("proof block in proof section" in task["title"].lower() for task in tasks))
            self.assertFalse(any("the current market leader" in task["title"].lower() for task in tasks))
            self.assertFalse(any("the strongest visible competitor" in task["title"].lower() for task in tasks))

    def test_pressure_cases_prefer_three_action_tasks_with_cleaner_wording(self) -> None:
        payload = {
            "job_request": {
                "job_id": "job_pressure_diverse_mix",
                "app_id": "consultant_followup_web",
                "project_id": "project_pressure_diverse_mix",
                "priority_class": "normal",
                "job_class": "light",
                "submitted_at": "2026-03-24T10:00:00+00:00",
                "requested_capability": "followup_task_recommendation",
                "input_payload": {
                    "context_type": "working_document",
                    "prompt": "Identify competitive signals and return exactly 3 actionable follow-up tasks.",
                    "artifacts": [{"type": "upload", "ref": "source_pressure_diverse_mix"}],
                },
                "source_refs": ["source_pressure_diverse_mix"],
            },
            "source_package": {
                "project_id": "project_pressure_diverse_mix",
                "source_kind": "manual_text",
                "project_summary": "managed_on_worker",
                "raw_text": (
                    "FlowOps raised onboarding and pricing friction in the SEO market. "
                    "Competitors are using testimonials, proof blocks, integration claims, and comparison messaging. "
                    "One exposed operator is reducing staff and may sell assets. "
                    "Trial-led acquisition pressure is rising."
                ),
                "source_ref": "source_pressure_diverse_mix",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            result = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))

            tasks = result["job_result"]["result_payload"]["recommended_tasks"]
            titles = [task["title"].lower() for task in tasks]
            buckets = {task["move_bucket"] for task in tasks}

            self.assertEqual(len(tasks), 3)
            self.assertNotEqual(tasks[2]["task_type"], "information_request")
            self.assertGreaterEqual(len(buckets), 3)
            self.assertFalse(any("the current market leader" in title for title in titles))
            self.assertFalse(any("the strongest visible competitor" in title for title in titles))
            self.assertFalse(any("proof block in proof section" in title for title in titles))

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
                    "current_tasks": first_tasks,
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
            self.assertIn(first_tasks[1]["title"], [t["title"] for t in regenerated])
            self.assertIn(first_tasks[2]["title"], [t["title"] for t in regenerated])
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
                    "current_tasks": first_tasks,
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
            self.assertIn(first_tasks[0]["title"], [t["title"] for t in regenerated])
            self.assertIn(first_tasks[1]["title"], [t["title"] for t in regenerated])
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
                    "current_tasks": first["job_result"]["result_payload"]["recommended_tasks"],
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
            regenerated = response["job_result"]["result_payload"]["recommended_tasks"]
            regenerated_titles = [task["title"] for task in regenerated]
            self.assertEqual(len(regenerated), 3)
            self.assertIn("Rewrite the pricing page hero this week to answer the strongest proof and trial pressure before buyers default to Fortitude AI", regenerated_titles)
            self.assertIn(first["job_result"]["result_payload"]["recommended_tasks"][0]["title"], regenerated_titles)
            self.assertIn(first["job_result"]["result_payload"]["recommended_tasks"][2]["title"], regenerated_titles)
            memory_rows = list_generation_memory_rows("project_feedback_edit", path=db_path)
            self.assertTrue(any(row["memory_kind"] == "prefer_channel" for row in memory_rows))

    def test_deleted_and_held_tasks_regenerate_without_repeating_same_title(self) -> None:
        payload = {
            "job_request": {
                "job_id": "job_feedback_delete_hold",
                "app_id": "consultant_followup_web",
                "project_id": "project_feedback_delete_hold",
                "priority_class": "normal",
                "job_class": "light",
                "submitted_at": "2026-03-23T15:40:00+00:00",
                "requested_capability": "followup_task_recommendation",
                "input_payload": {
                    "context_type": "working_document",
                    "prompt": "Analyze the uploaded market document and return actions.",
                    "artifacts": [{"type": "upload", "ref": "source_feedback_delete_hold"}],
                },
                "source_refs": ["source_feedback_delete_hold"],
            },
            "source_package": {
                "project_id": "project_feedback_delete_hold",
                "source_kind": "manual_text",
                "project_summary": "managed_on_worker",
                "raw_text": (
                    "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, "
                    "trial offers, customer testimonials, integration claims, and onboarding friction."
                ),
                "source_ref": "source_feedback_delete_hold",
                "file_name": "feedback-analysis.docx",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            first = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))
            first_tasks = first["job_result"]["result_payload"]["recommended_tasks"]
            response = process_task_feedback(
                "project_feedback_delete_hold",
                {
                    "job_id": "job_feedback_delete_hold",
                    "current_tasks": first_tasks,
                    "task_feedback_items": [
                        {
                            "feedback_id": "task_feedback_delete_hold_1",
                            "rank": 1,
                            "original_title": first_tasks[0]["title"],
                            "original_expected_advantage": first_tasks[0]["expected_advantage"],
                            "feedback_type": "deleted_with_annotation",
                            "feedback_comment": "Avoid this phrase in the live checklist.",
                        },
                        {
                            "feedback_id": "task_feedback_delete_hold_2",
                            "rank": 2,
                            "original_title": first_tasks[1]["title"],
                            "original_expected_advantage": first_tasks[1]["expected_advantage"],
                            "feedback_type": "held_for_later",
                            "feedback_comment": "Useful later, not this week.",
                        },
                    ],
                },
                WorkerBridgeConfig(local_db_path=db_path),
            )
            regenerated = response["job_result"]["result_payload"]["recommended_tasks"]
            regenerated_titles = [task["title"] for task in regenerated]
            self.assertEqual(len(regenerated), 3)
            self.assertNotIn(first_tasks[0]["title"], regenerated_titles)
            self.assertNotIn(first_tasks[1]["title"], regenerated_titles)
            self.assertIn(first_tasks[2]["title"], regenerated_titles)
            memory_rows = list_generation_memory_rows("project_feedback_delete_hold", path=db_path)
            self.assertTrue(any(row["memory_kind"] == "avoid_title" for row in memory_rows))

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

    def test_pressure_cases_do_not_leak_fake_competitors_or_default_to_request_third_task(self) -> None:
        payload = {
            "job_request": {
                "job_id": "job_pressure_regression",
                "app_id": "consultant_followup_web",
                "project_id": "project_pressure_regression",
                "priority_class": "normal",
                "job_class": "light",
                "submitted_at": "2026-03-24T18:00:00+00:00",
                "requested_capability": "followup_task_recommendation",
                "input_payload": {
                    "context_type": "working_document",
                    "prompt": "Turn these messy notes into the next three useful business moves.",
                    "artifacts": [{"type": "upload", "ref": "source_pressure_regression"}],
                },
            },
            "source_package": {
                "project_id": "project_pressure_regression",
                "source_kind": "manual_text",
                "project_summary": "managed_on_worker",
                "raw_text": (
                    "Notes: buyers keep asking if setup is heavy, two prospects mentioned Fortitude AI's free trial, "
                    "pricing page doesn't answer onboarding objections, homepage proof is weak, sales calls keep rebuilding the same comparison manually."
                ),
                "source_ref": "source_pressure_regression",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            result = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))
            tasks = result["job_result"]["result_payload"]["recommended_tasks"]
            combined = " ".join(
                [task["title"] + " " + task["why_now"] + " " + task["expected_advantage"] for task in tasks]
            ).lower()

            self.assertNotIn("notes's", combined)
            self.assertNotIn("its first", combined)
            self.assertNotIn("trial's trial", combined)
            self.assertNotIn("fortitude ai focus", combined)
            self.assertGreaterEqual(sum(task["task_type"] != "information_request" for task in tasks), 2)
            self.assertNotEqual(tasks[2]["task_type"], "information_request")


if __name__ == "__main__":
    unittest.main()
