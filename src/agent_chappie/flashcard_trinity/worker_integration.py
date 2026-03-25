"""Build intelligence_cards + card_scores from MLX Trinity (optional worker path)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from agent_chappie.flashcard_trinity.logutil import get_logger, trinity_debug_enabled
from agent_chappie.flashcard_trinity.pipeline import TrinityConfig, TrinityPipelineResult, run_trinity
from agent_chappie.flashcard_trinity.schemas import TrinityFlashcardRow
from agent_chappie.observation_engine import SourcePackage

_log = get_logger()


@dataclass
class TrinityWorkerResult:
    """Outcome of attempting Trinity for one job (IMP-04)."""

    cards: list[dict[str, Any]]
    scores: list[dict[str, Any]]
    used_trinity_cards: bool
    detail: dict[str, Any]


def mlx_trinity_enabled() -> bool:
    """True when Trinity flashcards are enabled (preferred or legacy env name)."""
    for key in ("FLASHCARD_MLX_TRINITY", "FLASHCARD_MLX_TRIAD"):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def heuristic_flashcards_allowed() -> bool:
    """When Trinity is on, heuristic fallback requires AGENT_ALLOW_HEURISTIC_FLASHCARDS (T-U02)."""
    return os.environ.get("AGENT_ALLOW_HEURISTIC_FLASHCARDS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _unique_strs(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _compose_document_excerpt(
    source_package: SourcePackage,
    atomic_facts: list[dict[str, Any]],
    max_chars: int,
) -> str:
    parts: list[str] = []
    if source_package.project_summary:
        parts.append(str(source_package.project_summary).strip())
    if source_package.raw_text:
        parts.append(str(source_package.raw_text).strip())
    for fact in atomic_facts[:100]:
        clause = fact.get("clause_text")
        if clause:
            parts.append(str(clause).strip()[:500])
        else:
            parts.append(str(fact.get("fact_value", ""))[:300])
    blob = "\n\n".join(p for p in parts if p)
    return blob[:max_chars]


def _match_fact_refs(combined_text: str, atomic_facts: list[dict[str, Any]]) -> list[str]:
    lowered = combined_text.lower()
    out: list[str] = []
    for fact in atomic_facts:
        fid = str(fact.get("fact_id") or "")
        if not fid:
            continue
        ct = str(fact.get("clause_text") or "").strip()
        if len(ct) < 6:
            continue
        fragment = ct.lower()[:80]
        if fragment in lowered or ct.lower() in lowered:
            out.append(fid)
    return _unique_strs(out)[:16]


def _default_source_refs(rows: list[dict[str, Any]], limit: int = 8) -> list[str]:
    refs = [str(r.get("source_ref") or "").strip() for r in rows]
    return _unique_strs([r for r in refs if r])[:limit]


def _run_trinity_subprocess(doc: str, _cfg: TrinityConfig, timeout_sec: float) -> TrinityPipelineResult:
    """Hard wall-clock bound: child process is killed on timeout (TRINITY_SUBPROCESS=1)."""
    cmd = [sys.executable, "-m", "agent_chappie.flashcard_trinity.subprocess_entry"]
    try:
        proc = subprocess.run(
            cmd,
            input=doc,
            text=True,
            capture_output=True,
            timeout=timeout_sec if timeout_sec > 0 else None,
            check=False,
            cwd=os.getcwd(),
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired as exc:
        _log.error(
            "Trinity subprocess exceeded timeout=%s; process killed.",
            timeout_sec,
        )
        if exc.process is not None:
            try:
                exc.process.kill()
            except ProcessLookupError:
                pass
        return TrinityPipelineResult(
            rows=[],
            stats={
                "drafter_atoms": 0,
                "writer_pairs": 0,
                "judge_verdicts": 0,
                "rows_kept": 0,
                "quarantine_rows": 0,
                "filtered_below_threshold": 0,
                "hybrid_rule_rejects": 0,
                "timeout": True,
                "drop_reason_counts": {},
                "timings_ms": {},
            },
            quarantine_rows=[],
        )
    if proc.returncode != 0:
        _log.warning(
            "Trinity subprocess exit=%s stderr=%s",
            proc.returncode,
            (proc.stderr or "")[:500],
        )
        return TrinityPipelineResult(
            rows=[],
            stats={
                "drafter_atoms": 0,
                "writer_pairs": 0,
                "judge_verdicts": 0,
                "rows_kept": 0,
                "quarantine_rows": 0,
                "filtered_below_threshold": 0,
                "hybrid_rule_rejects": 0,
                "subprocess_error": True,
                "returncode": proc.returncode,
                "drop_reason_counts": {},
                "timings_ms": {},
            },
            quarantine_rows=[],
        )
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        _log.warning("Trinity subprocess invalid JSON: %s", exc)
        return TrinityPipelineResult(
            rows=[],
            stats={
                "drafter_atoms": 0,
                "writer_pairs": 0,
                "judge_verdicts": 0,
                "rows_kept": 0,
                "quarantine_rows": 0,
                "filtered_below_threshold": 0,
                "hybrid_rule_rejects": 0,
                "subprocess_json_error": True,
                "drop_reason_counts": {},
                "timings_ms": {},
            },
            quarantine_rows=[],
        )
    rows = [TrinityFlashcardRow.model_validate(x) for x in data.get("rows") or []]
    qrows = [TrinityFlashcardRow.model_validate(x) for x in data.get("quarantine_rows") or []]
    stats = data.get("stats") or {}
    return TrinityPipelineResult(rows=rows, stats=stats, quarantine_rows=qrows)


def _run_trinity_with_wall_clock(
    doc: str,
    cfg: TrinityConfig,
    *,
    job_id: str = "",
    progress_hook: Any = None,
) -> TrinityPipelineResult:
    """IMP-07: optional wall-clock bound — subprocess (hard kill) or thread pool."""
    sec = float(os.environ.get("TRINITY_MAX_WALL_SECONDS", "0") or 0)
    use_sub = os.environ.get("TRINITY_SUBPROCESS", "").strip().lower() in ("1", "true", "yes", "on")
    if use_sub and sec > 0:
        return _run_trinity_subprocess(doc, cfg, sec)
    if sec <= 0:
        return run_trinity(doc, cfg, job_id=job_id, progress_hook=progress_hook)
    from concurrent.futures import ThreadPoolExecutor
    from concurrent.futures import TimeoutError as FuturesTimeoutError

    def _call() -> TrinityPipelineResult:
        return run_trinity(doc, cfg, job_id=job_id, progress_hook=progress_hook)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_call)
        try:
            return future.result(timeout=sec)
        except FuturesTimeoutError:
            _log.error(
                "Trinity exceeded TRINITY_MAX_WALL_SECONDS=%s (thread may still be running)",
                sec,
            )
            return TrinityPipelineResult(
                rows=[],
                stats={
                    "drafter_atoms": 0,
                    "writer_pairs": 0,
                    "judge_verdicts": 0,
                    "rows_kept": 0,
                    "quarantine_rows": 0,
                    "filtered_below_threshold": 0,
                    "hybrid_rule_rejects": 0,
                    "timeout": True,
                    "drop_reason_counts": {},
                    "timings_ms": {},
                },
                quarantine_rows=[],
            )


def _progress_hook_factory(job_id: str):
    if not job_id or os.environ.get("TRINITY_PROGRESS_PERSIST", "").strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return None

    def hook(payload: dict[str, Any]) -> None:
        try:
            from agent_chappie.local_store import record_trinity_atom_progress

            pid = payload.get("project_id")
            if not pid:
                return
            stage = str(payload.get("stage") or "unknown")
            atom_index = int(payload.get("atom_index", -1))
            slim = {k: v for k, v in payload.items() if k not in ("project_id",)}
            record_trinity_atom_progress(
                str(pid),
                job_id,
                stage,
                slim,
                atom_index=atom_index,
            )
        except Exception:
            if trinity_debug_enabled():
                _log.debug("trinity progress_hook failed", exc_info=True)

    return hook


def _row_to_card_score(
    project_id: str,
    row: TrinityFlashcardRow,
    *,
    quarantined: bool,
    atomic_facts: list[dict[str, Any]],
    refreshed_sources: list[dict[str, Any]],
    weight_profile: dict[str, float],
    now: datetime,
    seq: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    card_id = f"card:{uuid.uuid4()}"
    combined = f"{row.drafter_text}\n{row.enriched_text}"
    fact_refs = _match_fact_refs(combined, atomic_facts)
    source_refs = _default_source_refs(refreshed_sources)
    if not fact_refs and not source_refs:
        source_refs = ["synthetic::mlx_trinity"]

    expires_at = now + timedelta(days=5 + seq % 3)
    expires_iso = expires_at.isoformat().replace("+00:00", "Z")

    confidence = float(row.final_confidence)
    impact_score = min(98.0, max(30.0, 30.0 + 68.0 * float(row.final_impact)))
    if quarantined:
        impact_score = min(impact_score, 30.0)

    freshness_score = max(0.05, min(1.0, (expires_at - now).total_seconds() / (10 * 24 * 3600)))
    ref_count = len(fact_refs)
    evidence_strength = max(0.15, min(1.0, ref_count / 6.0 if ref_count else 0.35))
    w_conf = float(weight_profile.get("w_confidence", 0.45))
    w_imp = float(weight_profile.get("w_impact", 0.40))
    w_urg = float(weight_profile.get("w_urgency", 0.15))
    rank_score = w_conf * confidence + w_imp * (impact_score / 100.0) + w_urg * freshness_score
    if quarantined:
        rank_score = 0.0
        confidence = 0.0

    gate_flags = row.hybrid_gate_flags or []
    card = {
        "card_id": card_id,
        "project_id": project_id,
        "insight": row.enriched_text[:2000],
        "implication": (row.implication or row.enriched_text)[:2000],
        "potential_moves": (row.potential_moves or [])[:3],
        "fact_refs": fact_refs,
        "source_refs": source_refs,
        "segment": "signals",
        "competitor": None,
        "channel": "key buyer-facing pages",
        "state": "quarantine" if quarantined else "candidate",
        "expires_at": expires_iso,
    }
    score = {
        "card_id": card_id,
        "project_id": project_id,
        "confidence": round(confidence, 3),
        "impact_score": round(impact_score, 2),
        "freshness_score": round(freshness_score, 3),
        "evidence_strength": round(evidence_strength, 3),
        "rank_score": round(rank_score, 6),
        "quarantine_reason": row.quarantine_reason if quarantined else None,
        "gate_flags_json": json.dumps(gate_flags, ensure_ascii=False) if gate_flags else None,
    }
    return card, score


def build_cards_and_scores_from_mlx_trinity(
    project_id: str,
    source_package: SourcePackage,
    atomic_facts: list[dict[str, Any]],
    refreshed_sources: list[dict[str, Any]],
    weight_profile: dict[str, float],
    *,
    cfg: TrinityConfig | None = None,
    job_id: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cfg = cfg or TrinityConfig.from_env()
    doc = _compose_document_excerpt(source_package, atomic_facts, cfg.max_input_chars)

    base_progress = _progress_hook_factory(job_id)

    def _wrapped_hook(payload: dict[str, Any]) -> None:
        if base_progress:
            base_progress({**payload, "project_id": project_id})

    outp = _run_trinity_with_wall_clock(doc, cfg, job_id=job_id, progress_hook=_wrapped_hook)

    if not outp.rows and not outp.quarantine_rows:
        if trinity_debug_enabled():
            _log.debug(
                "Trinity returned zero rows after pipeline (project_id=%s doc_excerpt_len=%s stats=%s)",
                project_id,
                len(doc),
                outp.stats,
            )
        return [], [], dict(outp.stats)

    now = datetime.now(UTC)
    cards: list[dict[str, Any]] = []
    scores: list[dict[str, Any]] = []
    seq = 0

    for row in outp.rows:
        c, s = _row_to_card_score(
            project_id,
            row,
            quarantined=False,
            atomic_facts=atomic_facts,
            refreshed_sources=refreshed_sources,
            weight_profile=weight_profile,
            now=now,
            seq=seq,
        )
        cards.append(c)
        scores.append(s)
        seq += 1

    for row in outp.quarantine_rows:
        c, s = _row_to_card_score(
            project_id,
            row,
            quarantined=True,
            atomic_facts=atomic_facts,
            refreshed_sources=refreshed_sources,
            weight_profile=weight_profile,
            now=now,
            seq=seq,
        )
        cards.append(c)
        scores.append(s)
        seq += 1

    st = dict(outp.stats)
    st["promoted_cards"] = len(outp.rows)
    st["quarantine_cards"] = len(outp.quarantine_rows)
    return cards, scores, st


def try_mlx_trinity_cards(
    project_id: str,
    source_package: SourcePackage,
    atomic_facts: list[dict[str, Any]],
    refreshed_sources: list[dict[str, Any]],
    weight_profile: dict[str, float],
    *,
    job_id: str = "",
) -> TrinityWorkerResult | None:
    if not mlx_trinity_enabled():
        return None
    try:
        from agent_chappie.flashcard_trinity.mlx_runner import mlx_available

        if not mlx_available():
            msg = (
                "Trinity enabled (FLASHCARD_MLX_TRINITY) but mlx_lm is not available. "
                "Install requirements-mlx-flashcards.txt or set AGENT_ALLOW_HEURISTIC_FLASHCARDS=1."
            )
            _log.warning(msg)
            return TrinityWorkerResult(
                [],
                [],
                False,
                {"outcome": "mlx_unavailable"},
            )
    except Exception as exc:
        _log.warning(
            "Trinity: mlx availability check failed: %s",
            exc,
            exc_info=trinity_debug_enabled(),
        )
        return TrinityWorkerResult(
            [],
            [],
            False,
            {"outcome": "mlx_check_error", "error": str(exc)},
        )
    try:
        cards, scores, stats = build_cards_and_scores_from_mlx_trinity(
            project_id,
            source_package,
            atomic_facts,
            refreshed_sources,
            weight_profile,
            job_id=job_id,
        )
    except Exception as exc:
        _log.warning(
            "Trinity run failed for project_id=%s: %s",
            project_id,
            exc,
            exc_info=trinity_debug_enabled(),
        )
        return TrinityWorkerResult(
            [],
            [],
            False,
            {"outcome": "trinity_error", "error": str(exc)},
        )

    detail = dict(stats)
    if stats.get("timeout"):
        detail["outcome"] = "trinity_timeout"
        _log.warning(
            "Trinity timed out for project_id=%s; falling back to heuristic flashcards unless strict mode.",
            project_id,
        )
        return TrinityWorkerResult([], [], False, detail)

    if cards:
        detail["outcome"] = "trinity_success"
        return TrinityWorkerResult(cards, scores, True, detail)

    detail["outcome"] = "trinity_empty"
    _log.warning(
        "Trinity produced no cards for project_id=%s; falling back to heuristic flashcards unless strict mode. "
        "Set FLASHCARD_MLX_TRINITY_DEBUG=1 (or FLASHCARD_MLX_DEBUG=1) for per-stage logs.",
        project_id,
    )
    return TrinityWorkerResult([], [], False, detail)
