from __future__ import annotations

import base64
import os
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.observation_engine import (
    SourcePackage,
    deduplicate_observations,
    extract_uploaded_file_text,
    extract_observations,
    generate_recommended_tasks,
    infer_context,
    repair_recommended_tasks,
)
from agent_chappie.validation import ValidationError, validate_job_result
from agent_chappie.local_store import (
    fetch_knowledge_rows,
    initialize_local_store,
    insert_observations,
    list_recent_observations,
    save_source_snapshot,
    update_monitor_state,
    upsert_knowledge_state,
)


class ObservationEngineTests(unittest.TestCase):
    def test_extract_observations_finds_pricing_and_proof_signals(self) -> None:
        source = SourcePackage(
            project_id="project_001",
            source_kind="manual_text",
            project_summary="Regional soccer academy review",
            raw_text="FlowOps launched a discount voucher and added customer logos with testimonials above the fold.",
            source_ref="source_001",
            competitor="FlowOps",
            region="north_cluster",
        )
        observations = extract_observations(source)
        signal_types = {observation["signal_type"] for observation in observations}
        self.assertIn("offer", signal_types)
        self.assertIn("proof_signal", signal_types)

    def test_extract_observations_keeps_atomic_competitor_specific_signals(self) -> None:
        source = SourcePackage(
            project_id="project_002",
            source_kind="manual_text",
            project_summary="North Cluster soccer academy",
            raw_text="FlowOps raised U14 prices by 15%, Essex County Club launched a free-trial campaign, and Westover Academy may close before the next intake.",
            source_ref="source_002",
        )
        observations = extract_observations(source)
        summaries = {observation["summary"] for observation in observations}
        competitors = {observation["competitor"] for observation in observations}
        self.assertIn("FlowOps", competitors)
        self.assertIn("Essex County Club", competitors)
        self.assertIn("Westover Academy", competitors)
        self.assertTrue(any("raised U14 prices by 15%" in summary for summary in summaries))
        self.assertTrue(any("free-trial campaign" in summary for summary in summaries))

    def test_extract_observations_skips_offer_for_legal_hearsay_copy(self) -> None:
        source = SourcePackage(
            project_id="project_law",
            source_kind="manual_text",
            project_summary="Competitive memo",
            raw_text=(
                "Hearsay is defined as an out of court statement offered in court to prove "
                "the truth of the matter asserted in the statement."
            ),
            source_ref="source_law",
        )
        observations = extract_observations(source)
        signal_types = {observation["signal_type"] for observation in observations}
        self.assertNotIn("offer", signal_types)

    def test_extract_observations_ignores_negated_signal_clauses(self) -> None:
        source = SourcePackage(
            project_id="project_negated",
            source_kind="manual_text",
            project_summary="Managed on worker",
            raw_text=(
                "There is no pricing change this month, no discount campaign, and no closure signal. "
                "Fortitude AI added testimonials and customer logos above the fold."
            ),
            source_ref="source_negated",
        )
        observations = extract_observations(source)
        signal_types = {observation["signal_type"] for observation in observations}
        self.assertEqual(signal_types, {"messaging_shift", "proof_signal"})

    def test_deduplicate_observations_ignores_similar_recent_signal(self) -> None:
        source = SourcePackage(
            project_id="project_001",
            source_kind="manual_text",
            project_summary="Regional soccer academy review",
            raw_text="FlowOps launched a discount voucher this week.",
            source_ref="source_001",
            competitor="FlowOps",
            region="north_cluster",
        )
        observations = extract_observations(source)
        deduped = deduplicate_observations(observations, observations)
        self.assertEqual(deduped, [])

    def test_generate_recommended_tasks_returns_ranked_actions(self) -> None:
        source = SourcePackage(
            project_id="project_001",
            source_kind="manual_text",
            project_summary="Regional soccer academy review",
            raw_text="FlowOps raised prices. Another nearby academy may close and sell equipment.",
            source_ref="source_001",
            competitor="FlowOps",
            region="north_cluster",
        )
        observations = extract_observations(source)
        result_payload = generate_recommended_tasks(source, observations)
        self.assertEqual(result_payload["recommended_tasks"][0]["rank"], 1)
        self.assertEqual(len(result_payload["recommended_tasks"]), 3)
        titles = [task["title"].lower() for task in result_payload["recommended_tasks"]]
        self.assertTrue(any("type=pricing_change" in title or "window=this_week" in title for title in titles))
        self.assertTrue(any("bundle=closure_plus_asset_sale" in t or "type=closure" in t for t in titles))
        self.assertTrue(any("conversion" in task["expected_advantage"].lower() for task in result_payload["recommended_tasks"]))
        self.assertTrue(any("summary=" in task["why_now"].lower() for task in result_payload["recommended_tasks"]))
        self.assertTrue(all("improve " not in title for title in titles))

    def test_generate_recommended_tasks_combines_multi_signal_pricing_and_offer(self) -> None:
        source = SourcePackage(
            project_id="project_003",
            source_kind="manual_text",
            project_summary="North Cluster soccer academy",
            raw_text=(
                "FlowOps raised U14 prices by 15%, Essex County Club launched a free-trial campaign, "
                "Westover Academy may close before the next intake, and Westover Academy started an equipment sell-off."
            ),
            source_ref="source_003",
        )
        observations = extract_observations(source)
        result_payload = generate_recommended_tasks(source, observations)
        top_task = result_payload["recommended_tasks"][0]
        self.assertEqual(len(result_payload["recommended_tasks"]), 3)
        self.assertGreaterEqual(len(top_task["evidence_refs"]), 2)
        self.assertIn("bundle=pricing_plus_offer", top_task["title"].lower())
        self.assertIn("flowops", top_task["why_now"].lower())
        self.assertIn("essex county club", top_task["why_now"].lower())
        self.assertIn("measurable_axes", top_task["expected_advantage"].lower())

    def test_infer_context_recovers_competitor_and_region_for_fresh_project(self) -> None:
        inferred = infer_context(
            "Essex County Club launched a free-trial campaign for North Cluster families.",
            "managed_on_worker",
        )
        self.assertEqual(inferred["competitor"], "Essex County Club")
        self.assertEqual(inferred["region"], "north_cluster")
        self.assertGreaterEqual(float(inferred["confidence"]), 0.9)

    def test_extract_uploaded_docx_text(self) -> None:
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>FlowOps raised U14 prices by 15% in North Cluster.</w:t></w:r></w:p></w:body>"
            "</w:document>"
        )
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", xml)

        source = SourcePackage(
            project_id="project_docx",
            source_kind="uploaded_file",
            project_summary="managed_on_worker",
            raw_text="pricing_notes.docx",
            source_ref="source_docx",
            file_name="pricing_notes.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content_base64=base64.b64encode(buffer.getvalue()).decode("utf-8"),
        )

        extracted = extract_uploaded_file_text(source)
        self.assertIn("pricing_notes.docx", extracted)
        self.assertIn("FlowOps raised U14 prices by 15%", extracted)

    def test_repair_recommended_tasks_rewrites_vague_expected_advantage(self) -> None:
        source = SourcePackage(
            project_id="project_repair",
            source_kind="manual_text",
            project_summary="North Cluster soccer academy",
            raw_text="FlowOps raised U14 prices by 15% and Essex County Club launched a free-trial campaign.",
            source_ref="source_repair",
        )
        observations = extract_observations(source)
        payload = {
            "recommended_tasks": [
                {
                    "rank": 1,
                    "title": "Launch a 7-day switch campaign with a free trial for U14 families before Essex County Club and FlowOps reset the north cluster market",
                    "why_now": "FlowOps raised pricing while Essex County Club pushed free trial messaging in north cluster.",
                    "expected_advantage": "Creates advantage quickly.",
                    "evidence_refs": [observations[0]["signal_id"], observations[1]["signal_id"]],
                },
                {
                    "rank": 2,
                    "title": "Update the U14 pricing page and launch a 7-day comparison offer against FlowOps",
                    "why_now": "FlowOps changed pricing in north cluster: FlowOps raised U14 prices by 15%.",
                    "expected_advantage": "Improves positioning.",
                    "evidence_refs": [observations[0]["signal_id"]],
                },
                {
                    "rank": 3,
                    "title": "Add a free trial response to the enrollment page this week",
                    "why_now": "Essex County Club launched a free-trial campaign in north cluster.",
                    "expected_advantage": "Helps a lot.",
                    "evidence_refs": [observations[1]["signal_id"]],
                },
            ],
            "summary": "Three actions.",
        }
        with self.assertRaises(ValidationError):
            validate_job_result(
                {
                    "job_id": "job_bad",
                    "app_id": "app",
                    "project_id": source.project_id,
                    "status": "complete",
                    "completed_at": "2026-03-23T12:00:00Z",
                    "result_payload": payload,
                }
            )
        repaired = repair_recommended_tasks(source, observations, payload)
        self.assertIsNotNone(repaired)
        assert repaired is not None
        self.assertTrue(any("conversion" in task["expected_advantage"].lower() or "intake" in task["expected_advantage"].lower() for task in repaired["recommended_tasks"]))

    def test_repair_recommended_tasks_returns_none_when_evidence_missing(self) -> None:
        source = SourcePackage(
            project_id="project_repair_none",
            source_kind="manual_text",
            project_summary="North Cluster soccer academy",
            raw_text="FlowOps raised U14 prices by 15%.",
            source_ref="source_repair_none",
        )
        observations = extract_observations(source)
        payload = {
            "recommended_tasks": [
                {
                    "rank": 1,
                    "title": "Launch a 7-day switch campaign this week",
                    "why_now": "FlowOps raised pricing in north cluster.",
                    "expected_advantage": "Better outcome.",
                    "evidence_refs": ["missing_signal"],
                },
                {
                    "rank": 2,
                    "title": "Update the pricing page this week",
                    "why_now": "FlowOps raised pricing in north cluster.",
                    "expected_advantage": "Better outcome.",
                    "evidence_refs": ["missing_signal"],
                },
                {
                    "rank": 3,
                    "title": "Add a comparison offer this week",
                    "why_now": "FlowOps raised pricing in north cluster.",
                    "expected_advantage": "Better outcome.",
                    "evidence_refs": ["missing_signal"],
                },
            ],
            "summary": "Three actions.",
        }
        self.assertIsNone(repair_recommended_tasks(source, observations, payload))

    def test_local_store_persists_observations_and_knowledge(self) -> None:
        source = SourcePackage(
            project_id="project_001",
            source_kind="manual_text",
            project_summary="Regional soccer academy review",
            raw_text="FlowOps raised prices.",
            source_ref="source_001",
            competitor="FlowOps",
            region="north_cluster",
        )
        observations = extract_observations(source)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "agent_brain.sqlite3")
            initialize_local_store(db_path)
            save_source_snapshot(source.__dict__, "hash_001", db_path)
            insert_observations(source.project_id, observations, db_path)
            stored = list_recent_observations(source.project_id, source.region, db_path)
            self.assertEqual(len(stored), len(observations))
            upsert_knowledge_state(stored, db_path)
            knowledge_rows = fetch_knowledge_rows(source.project_id, db_path)
            self.assertEqual(len(knowledge_rows), 1)
            update_monitor_state("continuous_observation_loop", "processed", source.source_ref, {"count": 1}, db_path)
            self.assertTrue(os.path.exists(db_path))


if __name__ == "__main__":
    unittest.main()
