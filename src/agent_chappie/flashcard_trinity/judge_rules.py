"""Deterministic checks after the Judge LLM (IMP-03 hybrid Judge)."""

from __future__ import annotations

import re
from typing import Any

from agent_chappie.flashcard_trinity.schemas import JudgeVerdict, WriterEnriched

_PLACEHOLDER_FRAGMENTS = (
    "lorem ipsum",
    "todo:",
    "tbd",
    "[insert",
    "placeholder",
    "xxx",
    "asdfasdf",
    "coming soon",
)

# Rough heuristic: substantial non-Latin scripts in short strings (mixed-language risk)
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")


def _text_has_placeholder(text: str) -> bool:
    t = text.lower().strip()
    if len(t) < 4:
        return True
    return any(p in t for p in _PLACEHOLDER_FRAGMENTS)


def _mixed_script_risk(combined: str) -> bool:
    """Flag likely mixed-language noise in very short outputs."""
    if len(combined) < 40:
        return False
    has_latin = bool(re.search(r"[a-zA-Z]{4,}", combined))
    has_cjk = bool(_CJK_RE.search(combined))
    has_cyr = bool(_CYRILLIC_RE.search(combined))
    pairs = (has_latin and has_cjk, has_latin and has_cyr, has_cjk and has_cyr)
    return sum(1 for p in pairs if p) >= 1 and len(combined) < 200


def apply_hybrid_judge_rules(
    verdict: JudgeVerdict,
    enriched: WriterEnriched,
    *,
    min_implication_len: int = 12,
    min_enriched_len: int = 16,
) -> tuple[JudgeVerdict, list[str]]:
    """
    Return a possibly adjusted verdict and a list of gate flag strings.
    On any rule violation, j_conf and j_impact are set to 0.0 (conservative gate).
    """
    flags: list[str] = []
    impl = (verdict.implication or "").strip()
    enr = enriched.text.strip()

    if len(impl) < min_implication_len:
        flags.append("implication_too_short")
    if len(enr) < min_enriched_len:
        flags.append("enriched_too_short")
    if _text_has_placeholder(impl) or _text_has_placeholder(enr):
        flags.append("placeholder_language")
    combined = f"{impl}\n{enr}"
    if _mixed_script_risk(combined):
        flags.append("mixed_script_risk")

    if not flags:
        return verdict, []

    v = verdict.model_copy(
        update={
            "j_conf": 0.0,
            "j_impact": 0.0,
        }
    )
    return v, flags
