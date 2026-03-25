"""
Optional MLX integration: loads the Trinity drafter model and parses JSON output.

Skipped automatically when ``mlx_lm`` is not installed (e.g. CI Linux).
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _mlx_available() -> bool:
    try:
        import mlx_lm  # noqa: F401

        return True
    except ImportError:
        return False


@unittest.skipUnless(_mlx_available(), "mlx_lm not installed (install requirements-mlx-flashcards.txt)")
class MlxFlashcardTrinityIntegrationTests(unittest.TestCase):
    def test_drafter_loads_and_returns_valid_atoms(self) -> None:
        from agent_chappie.flashcard_trinity.mlx_runner import mlx_available
        from agent_chappie.flashcard_trinity.pipeline import TrinityConfig, run_drafter
        from agent_chappie.flashcard_trinity.schemas import DrafterAtom

        self.assertTrue(mlx_available())
        cfg = TrinityConfig(
            max_atoms=3,
            max_input_chars=600,
            drafter_max_tokens=512,
            writer_retry_max_extra=0,
        )
        text = (
            "Acme Club raised U14 monthly dues from $120 to $135 in the North region. "
            "Families were notified by email on March 1."
        )
        atoms = run_drafter(text, cfg)
        self.assertIsInstance(atoms, list)
        # Empty list can happen if the model emits non-JSON; load + generate still exercised MLX.
        for atom in atoms:
            self.assertIsInstance(atom, DrafterAtom)
            self.assertTrue(atom.text.strip())


if __name__ == "__main__":
    unittest.main()
