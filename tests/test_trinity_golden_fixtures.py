"""T-U07: regression on fixture JSON shapes (no MLX)."""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.flashcard_trinity.schemas import DrafterAtom


class TrinityGoldenFixtureTests(unittest.TestCase):
    def test_golden_drafter_fixture(self) -> None:
        path = os.path.join(ROOT, "tests", "fixtures", "trinity", "golden_drafter.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        atoms = [DrafterAtom.model_validate(x) for x in data]
        self.assertEqual(len(atoms), 2)
        self.assertGreater(len(atoms[0].text), 5)


if __name__ == "__main__":
    unittest.main()
