"""Sequential MLX Trinity: Gemma drafter → Granite writer → Qwen judge."""

from __future__ import annotations

import os
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable

from agent_chappie.flashcard_trinity.judge_rules import apply_hybrid_judge_rules
from agent_chappie.flashcard_trinity.json_tools import first_json_decode
from agent_chappie.flashcard_trinity.logutil import get_logger, trinity_debug_enabled
from agent_chappie.flashcard_trinity.mlx_runner import build_chat_prompt, with_loaded_model
from agent_chappie.flashcard_trinity.schemas import DrafterAtom, JudgeVerdict, TrinityFlashcardRow, WriterEnriched


@dataclass
class TrinityPipelineResult:
    """Promoted rows, quarantined rows (T-U03), and run statistics (IMP-02)."""

    rows: list[TrinityFlashcardRow]
    stats: dict[str, Any]
    quarantine_rows: list[TrinityFlashcardRow] = field(default_factory=list)


@dataclass(frozen=True)
class TrinityConfig:
    drafter_model: str = "mlx-community/gemma-3-270m-it-4bit"
    writer_model: str = "mlx-community/granite-4.0-h-350m-8bit"
    judge_model: str = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
    drafter_revision: str | None = None
    writer_revision: str | None = None
    judge_revision: str | None = None
    confidence_threshold: float = 0.5
    max_atoms: int = 24
    max_input_chars: int = 12000
    drafter_max_tokens: int = 2048
    writer_max_tokens: int = 512
    judge_max_tokens: int = 512
    writer_retry_low_judge_conf: float = 0.35
    writer_retry_max_extra: int = 2
    sequential_unload: bool = True

    @classmethod
    def from_env(cls) -> TrinityConfig:
        def _rev(key: str) -> str | None:
            v = (os.environ.get(key) or "").strip()
            return v or None

        return cls(
            drafter_model=os.environ.get("MLX_DRAFTER_MODEL", cls.drafter_model),
            writer_model=os.environ.get("MLX_WRITER_MODEL", cls.writer_model),
            judge_model=os.environ.get("MLX_JUDGE_MODEL", cls.judge_model),
            drafter_revision=_rev("MLX_DRAFTER_REVISION"),
            writer_revision=_rev("MLX_WRITER_REVISION"),
            judge_revision=_rev("MLX_JUDGE_REVISION"),
            confidence_threshold=float(os.environ.get("FLASHCARD_MLX_CONFIDENCE_THRESHOLD", "0.5")),
            max_atoms=int(os.environ.get("FLASHCARD_MLX_MAX_ATOMS", "24")),
            max_input_chars=int(os.environ.get("FLASHCARD_MLX_INPUT_CHARS", "12000")),
            writer_retry_max_extra=max(
                0,
                int(os.environ.get("FLASHCARD_MLX_WRITER_RETRY_EXTRA", "2")),
            ),
            writer_retry_low_judge_conf=float(
                os.environ.get("FLASHCARD_MLX_JUDGE_RETRY_THRESHOLD", str(cls.writer_retry_low_judge_conf))
            ),
            sequential_unload=os.environ.get("FLASHCARD_MLX_SEQUENTIAL_UNLOAD", "1").lower()
            not in ("0", "false", "no"),
        )


DRAFTER_SYSTEM = (
    "You are a precise analyst. Break the user's document into atomic, self-contained claims or facts. "
    "Respond with ONLY a JSON array (no markdown). Each element must be an object with keys: "
    '"text" (string), "d_conf" (number 0-1, certainty this atom is grounded in the input), '
    '"d_impact" (number 0-1, business relevance). Use at most MAX_ATOMS elements. '
    "Merge trivial duplicates. Numbers must be decimals between 0 and 1."
)

WRITER_SYSTEM = (
    "You enrich one intelligence atom into clear professional language for executives. "
    "Keep the rewritten text to at most two crisp sentences and under 220 characters—no preamble, no bullets. "
    "Respond with ONLY one JSON object (no markdown) with keys: "
    '"text" (rewritten, concise), "w_conf" (0-1, language fidelity to the atom), '
    '"w_impact" (0-1, strength of the business point).'
)

JUDGE_SYSTEM = (
    "You judge one flashcard candidate. Given drafter scores, writer scores, and both texts, "
    "respond with ONLY one JSON object (no markdown): "
    '"j_conf" (0-1, logical consistency and grounding), '
    '"j_impact" (0-1, strategic importance), '
    '"implication" (one sentence, under 160 characters, calm professional tone—no hype), '
    '"potential_moves" (array of exactly 3 strings; each under 100 characters, imperative voice, no jargon dumps). '
    "Be strict: low quality → low j_conf."
)

_FIELD_REPAIR_HINT = (
    "The judge needs a complete card: one implication sentence (20–160 chars, professional) "
    "and exactly 3 potential_moves (each under 100 chars). Keep w_conf/w_impact honest."
)


def _run_generate(model: Any, tokenizer: Any, system: str, user: str, max_tokens: int) -> str:
    from mlx_lm import generate
    from mlx_lm.sample_utils import make_sampler

    prompt = build_chat_prompt(tokenizer, system, user)
    return generate(
        model,
        tokenizer,
        prompt,
        verbose=False,
        max_tokens=max_tokens,
        sampler=make_sampler(0.0),
    )


def _quarantine_row(
    atom: DrafterAtom,
    enriched: WriterEnriched | None,
    verdict: JudgeVerdict | None,
    *,
    reason: str,
    hybrid_flags: list[str] | None = None,
) -> TrinityFlashcardRow:
    en_text = enriched.text if enriched else "[writer stage did not produce valid JSON]"
    w_conf = float(enriched.w_conf) if enriched else 0.0
    w_imp = float(enriched.w_impact) if enriched else 0.0
    if verdict:
        j_conf, j_imp = float(verdict.j_conf), float(verdict.j_impact)
        implication = (verdict.implication or en_text[:400]).strip() or atom.text[:400]
        moves = list(verdict.potential_moves[:3])
    else:
        j_conf, j_imp = 0.0, 0.0
        implication = atom.text[:400]
        moves = []
    fc = max(0.0, min(1.0, float(atom.d_conf) * w_conf * j_conf))
    fi = max(0.0, min(1.0, float(atom.d_impact) * w_imp * j_imp))
    if not moves:
        moves = ["Quarantined — not promoted"]
    return TrinityFlashcardRow(
        drafter_text=atom.text,
        enriched_text=en_text,
        d_conf=atom.d_conf,
        d_impact=atom.d_impact,
        w_conf=w_conf,
        w_impact=w_imp,
        j_conf=j_conf,
        j_impact=j_imp,
        final_confidence=fc,
        final_impact=fi,
        implication=implication[:2000],
        potential_moves=moves,
        hybrid_gate_flags=list(hybrid_flags or []),
        quarantine_reason=reason,
    )


def run_drafter(doc_excerpt: str, cfg: TrinityConfig) -> list[DrafterAtom]:
    user = (
        f"MAX_ATOMS={cfg.max_atoms}.\n\nDocument:\n{doc_excerpt[: cfg.max_input_chars]}\n\n"
        "Output the JSON array now."
    )

    def phase(model: Any, tokenizer: Any) -> list[DrafterAtom]:
        raw = _run_generate(model, tokenizer, DRAFTER_SYSTEM, user, cfg.drafter_max_tokens)
        decoded = first_json_decode(raw)
        if not isinstance(decoded, list):
            return []
        out: list[DrafterAtom] = []
        for item in decoded[: cfg.max_atoms]:
            if not isinstance(item, dict):
                continue
            try:
                out.append(DrafterAtom.model_validate(item))
            except Exception:
                continue
        return out

    return with_loaded_model(
        cfg.drafter_model,
        phase,
        sequential_unload=cfg.sequential_unload,
        revision=cfg.drafter_revision,
    )


def run_writer(
    atom: DrafterAtom,
    cfg: TrinityConfig,
    *,
    retry_hint: str = "",
) -> WriterEnriched | None:
    payload = atom.model_dump()
    user = f"Atom JSON:\n{payload}\n{retry_hint}\nOutput one JSON object only."

    def phase(model: Any, tokenizer: Any) -> WriterEnriched | None:
        raw = _run_generate(model, tokenizer, WRITER_SYSTEM, user, cfg.writer_max_tokens)
        decoded = first_json_decode(raw)
        if not isinstance(decoded, dict):
            return None
        try:
            return WriterEnriched.model_validate(decoded)
        except Exception:
            return None

    return with_loaded_model(
        cfg.writer_model,
        phase,
        sequential_unload=cfg.sequential_unload,
        revision=cfg.writer_revision,
    )


def run_judge(
    atom: DrafterAtom,
    enriched: WriterEnriched,
    cfg: TrinityConfig,
) -> JudgeVerdict | None:
    user = (
        "Drafter: "
        + atom.model_dump_json()
        + "\nWriter: "
        + enriched.model_dump_json()
        + "\nOutput one JSON object only."
    )

    def phase(model: Any, tokenizer: Any) -> JudgeVerdict | None:
        raw = _run_generate(model, tokenizer, JUDGE_SYSTEM, user, cfg.judge_max_tokens)
        decoded = first_json_decode(raw)
        if not isinstance(decoded, dict):
            return None
        try:
            return JudgeVerdict.model_validate(decoded)
        except Exception:
            return None

    return with_loaded_model(
        cfg.judge_model,
        phase,
        sequential_unload=cfg.sequential_unload,
        revision=cfg.judge_revision,
    )


def run_writer_batch(atoms: list[DrafterAtom], cfg: TrinityConfig) -> list[WriterEnriched | None]:
    if not atoms:
        return []

    def phase(model: Any, tokenizer: Any) -> list[WriterEnriched | None]:
        results: list[WriterEnriched | None] = []
        for atom in atoms:
            payload = atom.model_dump()
            user = f"Atom JSON:\n{payload}\nOutput one JSON object only."
            raw = _run_generate(model, tokenizer, WRITER_SYSTEM, user, cfg.writer_max_tokens)
            decoded = first_json_decode(raw)
            if not isinstance(decoded, dict):
                results.append(None)
                continue
            try:
                results.append(WriterEnriched.model_validate(decoded))
            except Exception:
                results.append(None)
        return results

    return with_loaded_model(
        cfg.writer_model,
        phase,
        sequential_unload=cfg.sequential_unload,
        revision=cfg.writer_revision,
    )


def run_judge_batch(
    pairs: list[tuple[DrafterAtom, WriterEnriched]],
    cfg: TrinityConfig,
) -> list[JudgeVerdict | None]:
    if not pairs:
        return []

    def phase(model: Any, tokenizer: Any) -> list[JudgeVerdict | None]:
        results: list[JudgeVerdict | None] = []
        for atom, enriched in pairs:
            user = (
                "Drafter: "
                + atom.model_dump_json()
                + "\nWriter: "
                + enriched.model_dump_json()
                + "\nOutput one JSON object only."
            )
            raw = _run_generate(model, tokenizer, JUDGE_SYSTEM, user, cfg.judge_max_tokens)
            decoded = first_json_decode(raw)
            if not isinstance(decoded, dict):
                results.append(None)
                continue
            try:
                results.append(JudgeVerdict.model_validate(decoded))
            except Exception:
                results.append(None)
        return results

    return with_loaded_model(
        cfg.judge_model,
        phase,
        sequential_unload=cfg.sequential_unload,
        revision=cfg.judge_revision,
    )


def _composite_confidence(atom: DrafterAtom, enriched: WriterEnriched, verdict: JudgeVerdict) -> float:
    return float(atom.d_conf) * float(enriched.w_conf) * float(verdict.j_conf)


def _needs_field_repair(verdict: JudgeVerdict) -> bool:
    impl = str(verdict.implication or "").strip()
    if len(impl) < 20:
        return True
    pm = [str(x).strip() for x in verdict.potential_moves if str(x).strip()]
    return len(pm) < 1


def run_trinity(
    doc_excerpt: str,
    cfg: TrinityConfig | None = None,
    *,
    job_id: str = "",
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
) -> TrinityPipelineResult:
    log = get_logger()
    cfg = cfg or TrinityConfig.from_env()
    stats: dict[str, Any] = {
        "drafter_atoms": 0,
        "writer_pairs": 0,
        "judge_verdicts": 0,
        "rows_kept": 0,
        "quarantine_rows": 0,
        "filtered_below_threshold": 0,
        "hybrid_rule_rejects": 0,
        "timeout": False,
        "drop_reason_counts": {},
        "timings_ms": {},
    }
    quarantine_rows: list[TrinityFlashcardRow] = []
    drop_counter: Counter[str] = Counter()

    def _ph(payload: dict[str, Any]) -> None:
        if progress_hook:
            if job_id:
                payload = {**payload, "job_id": job_id}
            progress_hook(payload)

    t0 = time.perf_counter()
    atoms = run_drafter(doc_excerpt, cfg)
    stats["timings_ms"]["drafter"] = round((time.perf_counter() - t0) * 1000, 2)
    if job_id:
        log.info(
            "trinity_timing job_id=%s stage=drafter duration_ms=%s atoms=%s",
            job_id,
            stats["timings_ms"]["drafter"],
            len(atoms),
        )
    stats["drafter_atoms"] = len(atoms)
    if not atoms:
        drop_counter["drafter_no_valid_atoms"] += 1
        stats["drop_reason_counts"] = dict(drop_counter)
        if trinity_debug_enabled():
            log.debug(
                "Trinity drafter returned no valid atoms (input_len=%s max_atoms=%s)",
                len(doc_excerpt),
                cfg.max_atoms,
            )
        return TrinityPipelineResult(rows=[], stats=stats, quarantine_rows=[])

    t1 = time.perf_counter()
    enriched_list = run_writer_batch(atoms, cfg)
    stats["timings_ms"]["writer_batch"] = round((time.perf_counter() - t1) * 1000, 2)
    if job_id:
        log.info(
            "trinity_timing job_id=%s stage=writer_batch duration_ms=%s",
            job_id,
            stats["timings_ms"]["writer_batch"],
        )

    dropped_writer = sum(1 for e in enriched_list if e is None)
    if dropped_writer and trinity_debug_enabled():
        log.debug("Trinity writer dropped %s/%s atoms (parse/validation failed)", dropped_writer, len(atoms))

    pairs: list[tuple[DrafterAtom, WriterEnriched]] = []
    for atom, enriched in zip(atoms, enriched_list, strict=False):
        if enriched is None:
            quarantine_rows.append(_quarantine_row(atom, None, None, reason="writer_parse_or_validate_fail"))
            drop_counter["writer_parse_or_validate_fail"] += 1
            _ph({"stage": "quarantine", "reason": "writer_parse_or_validate_fail", "drafter_text_len": len(atom.text)})
            continue
        pairs.append((atom, enriched))
    stats["writer_pairs"] = len(pairs)

    t2 = time.perf_counter()
    verdicts = run_judge_batch(pairs, cfg)
    stats["timings_ms"]["judge_batch"] = round((time.perf_counter() - t2) * 1000, 2)
    if job_id:
        log.info(
            "trinity_timing job_id=%s stage=judge_batch duration_ms=%s",
            job_id,
            stats["timings_ms"]["judge_batch"],
        )

    dropped_judge = sum(1 for v in verdicts if v is None)
    if dropped_judge and trinity_debug_enabled():
        log.debug("Trinity judge dropped %s/%s pairs (parse/validation failed)", dropped_judge, len(pairs))

    rows: list[TrinityFlashcardRow] = []
    filtered_by_threshold = 0
    hybrid_rule_rejects = 0

    for (atom, enriched), verdict in zip(pairs, verdicts, strict=False):
        if verdict is None:
            quarantine_rows.append(_quarantine_row(atom, enriched, None, reason="judge_parse_or_validate_fail"))
            drop_counter["judge_parse_or_validate_fail"] += 1
            _ph({"stage": "quarantine", "reason": "judge_parse_or_validate_fail"})
            continue

        stats["judge_verdicts"] += 1
        use_atom, use_en, use_verdict = atom, enriched, verdict

        # TR-R06: one targeted writer+judge pass when judge fields are too thin.
        if _needs_field_repair(use_verdict):
            again = run_writer(use_atom, cfg, retry_hint=_FIELD_REPAIR_HINT)
            if again is not None:
                v2 = run_judge(use_atom, again, cfg)
                if v2 is not None and not _needs_field_repair(v2):
                    use_en, use_verdict = again, v2

        if cfg.writer_retry_low_judge_conf > 0 and cfg.writer_retry_max_extra > 0:
            extra_done = 0
            while (
                extra_done < cfg.writer_retry_max_extra
                and use_verdict.j_conf < cfg.writer_retry_low_judge_conf
            ):
                extra_done += 1
                base_fc = _composite_confidence(use_atom, use_en, use_verdict)
                again = run_writer(
                    use_atom,
                    cfg,
                    retry_hint=(
                        f"Retry {extra_done}/{cfg.writer_retry_max_extra}: judge j_conf was "
                        f"{use_verdict.j_conf:.2f} (below {cfg.writer_retry_low_judge_conf:.2f}). "
                        "Shorten, remove speculation, and align strictly to the drafter atom."
                    ),
                )
                if again is None:
                    break
                v2 = run_judge(use_atom, again, cfg)
                if v2 is None:
                    break
                new_fc = _composite_confidence(atom, again, v2)
                if v2.j_conf > use_verdict.j_conf or new_fc > base_fc:
                    prev_j = use_verdict.j_conf
                    use_en, use_verdict = again, v2
                    if trinity_debug_enabled():
                        log.debug(
                            "Trinity writer+judge retry %s accepted (j_conf %.3f -> %.3f)",
                            extra_done,
                            prev_j,
                            use_verdict.j_conf,
                        )
                else:
                    if trinity_debug_enabled():
                        log.debug(
                            "Trinity writer+judge retry %s did not improve; stopping retries for this atom",
                            extra_done,
                        )
                    break

        use_verdict, hybrid_flags = apply_hybrid_judge_rules(use_verdict, use_en)
        if hybrid_flags:
            hybrid_rule_rejects += 1
            if trinity_debug_enabled():
                log.debug("Trinity hybrid Judge rules triggered: %s", hybrid_flags)

        fc = float(use_atom.d_conf) * float(use_en.w_conf) * float(use_verdict.j_conf)
        fi = float(use_atom.d_impact) * float(use_en.w_impact) * float(use_verdict.j_impact)
        fc = max(0.0, min(1.0, fc))
        fi = max(0.0, min(1.0, fi))

        if hybrid_flags:
            quarantine_rows.append(
                _quarantine_row(
                    use_atom,
                    use_en,
                    use_verdict,
                    reason="hybrid_judge_rules",
                    hybrid_flags=hybrid_flags,
                )
            )
            drop_counter["hybrid_judge_rules"] += 1
            _ph({"stage": "quarantine", "reason": "hybrid_judge_rules", "flags": hybrid_flags})
            continue

        if fc < cfg.confidence_threshold:
            filtered_by_threshold += 1
            quarantine_rows.append(
                _quarantine_row(use_atom, use_en, use_verdict, reason="below_confidence_threshold")
            )
            drop_counter["below_confidence_threshold"] += 1
            _ph({"stage": "quarantine", "reason": "below_confidence_threshold", "final_confidence": fc})
            continue

        moves = use_verdict.potential_moves
        if not moves:
            moves = [
                "Validate with a stakeholder",
                "Cross-check against latest source material",
                "Decide whether to act this week",
            ]
        rows.append(
            TrinityFlashcardRow(
                drafter_text=use_atom.text,
                enriched_text=use_en.text,
                d_conf=use_atom.d_conf,
                d_impact=use_atom.d_impact,
                w_conf=use_en.w_conf,
                w_impact=use_en.w_impact,
                j_conf=use_verdict.j_conf,
                j_impact=use_verdict.j_impact,
                final_confidence=fc,
                final_impact=fi,
                implication=use_verdict.implication or use_en.text[:400],
                potential_moves=moves[:3],
                hybrid_gate_flags=hybrid_flags,
                quarantine_reason=None,
            )
        )
        _ph({"stage": "atom_promoted", "final_confidence": fc})

    stats["filtered_below_threshold"] = filtered_by_threshold
    stats["hybrid_rule_rejects"] = hybrid_rule_rejects
    stats["rows_kept"] = len(rows)
    stats["quarantine_rows"] = len(quarantine_rows)
    stats["drop_reason_counts"] = dict(drop_counter)
    if filtered_by_threshold and trinity_debug_enabled():
        log.debug(
            "Trinity dropped %s cards below confidence_threshold=%s (kept %s)",
            filtered_by_threshold,
            cfg.confidence_threshold,
            len(rows),
        )
    return TrinityPipelineResult(rows=rows, stats=stats, quarantine_rows=quarantine_rows)
