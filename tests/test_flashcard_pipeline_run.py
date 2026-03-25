from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.local_store import (
    initialize_local_store,
    latest_flashcard_pipeline_run,
    record_flashcard_pipeline_run,
)


class FlashcardPipelineRunTests(unittest.TestCase):
    def test_record_and_count_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "brain.sqlite3")
            initialize_local_store(db_path)
            record_flashcard_pipeline_run(
                "job-1",
                "proj-1",
                "heuristic_fallback",
                reason="trinity_empty",
                detail={"rows_kept": 0},
                path=db_path,
            )
            import sqlite3

            con = sqlite3.connect(db_path)
            try:
                n = con.execute("select count(*) from flashcard_pipeline_runs").fetchone()[0]
                self.assertEqual(n, 1)
                row = con.execute(
                    "select pipeline_source, reason from flashcard_pipeline_runs limit 1"
                ).fetchone()
                self.assertEqual(row[0], "heuristic_fallback")
                self.assertEqual(row[1], "trinity_empty")
            finally:
                con.close()

    def test_latest_flashcard_pipeline_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "brain.sqlite3")
            initialize_local_store(db_path)
            record_flashcard_pipeline_run(
                "job-x",
                "proj-x",
                "trinity",
                detail={"outcome": "trinity_success"},
                path=db_path,
            )
            row = latest_flashcard_pipeline_run("proj-x", path=db_path)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row["pipeline_source"], "trinity")
            self.assertEqual(row["detail"].get("outcome"), "trinity_success")


if __name__ == "__main__":
    unittest.main()
