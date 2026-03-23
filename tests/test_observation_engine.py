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
)
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
        self.assertTrue(any("update the" in title for title in titles))
        self.assertTrue(any("bundled offer" in title or "call flowops" in title for title in titles))
        self.assertTrue(any("enrollment" in task["expected_advantage"].lower() for task in result_payload["recommended_tasks"]))
        self.assertTrue(any("raised prices" in task["why_now"].lower() for task in result_payload["recommended_tasks"]))
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
        self.assertIn("switch", top_task["title"].lower())
        self.assertIn("flowops", top_task["why_now"].lower())
        self.assertIn("essex county club", top_task["why_now"].lower())
        self.assertIn("intake window", top_task["expected_advantage"].lower())

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
