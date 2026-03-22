from __future__ import annotations

import os
import sys
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.observation_engine import (
    SourcePackage,
    deduplicate_observations,
    extract_observations,
    generate_recommended_tasks,
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
        self.assertLessEqual(len(result_payload["recommended_tasks"]), 3)

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
