from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.flashcard_trinity.schemas import DrafterAtom, TrinityFlashcardRow
from agent_chappie.worker_bridge import apply_visibility_top_percent, build_nba_tasks_from_cards


class TrinityQuarantineVisibilityTests(unittest.TestCase):
    def test_quarantine_never_visible_top_percent(self) -> None:
        cards = [
            {"card_id": "a", "state": "candidate", "insight": "x", "implication": "y", "potential_moves": ["m"]},
            {"card_id": "b", "state": "quarantine", "insight": "x2", "implication": "y2", "potential_moves": ["m2"]},
        ]
        scores = [
            {"card_id": "a", "rank_score": 0.1},
            {"card_id": "b", "rank_score": 0.99},
        ]
        all_c, vis = apply_visibility_top_percent(cards, scores, percent=0.5)
        states = {c["card_id"]: c["state"] for c in all_c}
        self.assertEqual(states["b"], "quarantine")
        self.assertEqual(len(vis), 1)
        self.assertEqual(vis[0]["card_id"], "a")

    def test_rank_zero_skipped_for_nba_when_three_good_exist(self) -> None:
        base = {
            "state": "active",
            "insight": "Concrete regional pricing insight for the business.",
            "implication": "Margin pressure appears in the next reporting cycle for North Cluster operations.",
            "potential_moves": ["Review pricing with finance", "Brief the leadership team", "Monitor competitor pages"],
            "fact_refs": ["f1"],
            "source_refs": ["s1"],
            "confidence": 0.72,
        }
        cards = [
            {**base, "card_id": "z", "rank_score": 0.0},
            {**base, "card_id": "a", "rank_score": 0.95},
            {**base, "card_id": "b", "rank_score": 0.9},
            {**base, "card_id": "c", "rank_score": 0.85},
        ]
        tasks = build_nba_tasks_from_cards(cards, top_n=3)
        self.assertEqual(len(tasks), 3)
        blob = json.dumps(tasks)
        self.assertNotIn("z", blob)


class TrinityPipelineQuarantineRowTests(unittest.TestCase):
    def test_quarantine_row_schema(self) -> None:
        atom = DrafterAtom(text="Hello world example", d_conf=0.5, d_impact=0.5)
        row = TrinityFlashcardRow(
            drafter_text=atom.text,
            enriched_text="[writer stage did not produce valid JSON]",
            d_conf=atom.d_conf,
            d_impact=atom.d_impact,
            w_conf=0.0,
            w_impact=0.0,
            j_conf=0.0,
            j_impact=0.0,
            final_confidence=0.0,
            final_impact=0.0,
            implication=atom.text[:80],
            potential_moves=["Quarantined — not promoted"],
            quarantine_reason="writer_parse_or_validate_fail",
        )
        self.assertEqual(row.quarantine_reason, "writer_parse_or_validate_fail")


if __name__ == "__main__":
    unittest.main()
