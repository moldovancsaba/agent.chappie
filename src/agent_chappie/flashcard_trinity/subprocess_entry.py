"""Run `run_trinity` in an isolated process for hard wall-clock kill (IMP-07).

Parent sets the same env as production (model IDs, revisions). stdin: UTF-8 document excerpt.
stdout: one JSON object with keys rows, quarantine_rows, stats (Pydantic dumps).

    python -m agent_chappie.flashcard_trinity.subprocess_entry < excerpt.txt
"""

from __future__ import annotations

import json
import sys

from agent_chappie.flashcard_trinity.pipeline import run_trinity
from agent_chappie.flashcard_trinity.schemas import TrinityFlashcardRow


def main() -> None:
    doc = sys.stdin.read()
    result = run_trinity(doc)
    out = {
        "rows": [r.model_dump(mode="json") for r in result.rows],
        "quarantine_rows": [r.model_dump(mode="json") for r in result.quarantine_rows],
        "stats": result.stats,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
