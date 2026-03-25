from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.flashcard_trinity.judge_rules import apply_hybrid_judge_rules
from agent_chappie.flashcard_trinity.schemas import JudgeVerdict, WriterEnriched


class TrinityJudgeRulesTests(unittest.TestCase):
    def test_clean_verdict_unchanged(self) -> None:
        v = JudgeVerdict(j_conf=0.8, j_impact=0.7, implication="Prices rose in Q1 affecting margin.", potential_moves=["a"])
        w = WriterEnriched(text="The club increased monthly dues for U14 families in March.", w_conf=0.9, w_impact=0.8)
        out, flags = apply_hybrid_judge_rules(v, w)
        self.assertEqual(flags, [])
        self.assertAlmostEqual(out.j_conf, 0.8)

    def test_placeholder_zeroes_judge_scores(self) -> None:
        v = JudgeVerdict(j_conf=0.9, j_impact=0.9, implication="TODO: fill this in later", potential_moves=[])
        w = WriterEnriched(text="Real content here with enough length for the rule.", w_conf=0.9, w_impact=0.8)
        out, flags = apply_hybrid_judge_rules(v, w)
        self.assertIn("placeholder_language", flags)
        self.assertEqual(out.j_conf, 0.0)
        self.assertEqual(out.j_impact, 0.0)

    def test_implication_too_short(self) -> None:
        v = JudgeVerdict(j_conf=0.9, j_impact=0.9, implication="short", potential_moves=[])
        w = WriterEnriched(text="Enough enriched body text here for the minimum.", w_conf=0.9, w_impact=0.8)
        out, flags = apply_hybrid_judge_rules(v, w)
        self.assertIn("implication_too_short", flags)
        self.assertEqual(out.j_conf, 0.0)


if __name__ == "__main__":
    unittest.main()
