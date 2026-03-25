from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.flashcard_trinity.json_tools import first_json_decode
from agent_chappie.flashcard_trinity.schemas import DrafterAtom, WriterEnriched


class FlashcardTrinityJsonTests(unittest.TestCase):
    def test_first_json_decode_array(self) -> None:
        raw = 'Prefix noise [{"text":"a","d_conf":0.5,"d_impact":0.7}] trailing'
        decoded = first_json_decode(raw)
        self.assertIsInstance(decoded, list)
        self.assertEqual(len(decoded), 1)

    def test_first_json_decode_fenced(self) -> None:
        raw = """Here:\n```json\n{"text":"x","w_conf":1,"w_impact":0.2}\n```"""
        decoded = first_json_decode(raw)
        self.assertIsInstance(decoded, dict)
        self.assertEqual(decoded.get("text"), "x")

    def test_drafter_atom_validation(self) -> None:
        atom = DrafterAtom.model_validate({"text": "  hello  ", "d_conf": 0.5, "d_impact": 0.9})
        self.assertEqual(atom.text, "hello")

    def test_writer_clamps_invalid_range_raises(self) -> None:
        with self.assertRaises(Exception):
            WriterEnriched.model_validate({"text": "a", "w_conf": 2, "w_impact": 0.1})

    def test_mlx_trinity_enabled_new_and_legacy_env(self) -> None:
        from agent_chappie.flashcard_trinity.worker_integration import mlx_trinity_enabled

        base = {k: v for k, v in os.environ.items() if k not in ("FLASHCARD_MLX_TRINITY", "FLASHCARD_MLX_TRIAD")}
        with patch.dict(os.environ, {**base, "FLASHCARD_MLX_TRINITY": "1"}, clear=True):
            self.assertTrue(mlx_trinity_enabled())
        with patch.dict(os.environ, {**base, "FLASHCARD_MLX_TRIAD": "true"}, clear=True):
            self.assertTrue(mlx_trinity_enabled())


if __name__ == "__main__":
    unittest.main()
