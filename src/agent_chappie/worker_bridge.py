from __future__ import annotations

import json
import math
import os
import uuid
import re
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agent_chappie.feedback_memory import (
    avoid_title_pattern_matches,
    extract_comment_signals,
    intel_card_text_fingerprint,
    normalize_task_key,
)
from agent_chappie.local_store import (
    get_card_weight_profile,
    clear_generation_memory,
    create_managed_job,
    create_managed_source,
    decay_generation_memory,
    delete_generation_memory_row,
    delete_source_snapshot,
    delete_managed_job,
    delete_managed_source,
    fetch_knowledge_feedback_rows,
    fetch_knowledge_rows,
    get_project_active_checklist,
    get_source_snapshot,
    initialize_local_store,
    insert_observations,
    list_draft_segment_feedback_rows,
    list_draft_segments,
    list_evidence_units,
    list_generation_memory_rows,
    list_held_tasks,
    list_intelligence_cards,
    list_task_feedback_rows,
    list_observations_for_source,
    list_managed_jobs,
    list_managed_sources,
    list_monitor_rows,
    list_recent_observations,
    list_recent_source_snapshots,
    replace_draft_segments,
    replace_evidence_units,
    replace_atomic_facts,
    restore_held_task,
    save_held_task,
    save_project_active_checklist,
    save_source_snapshot,
    save_generation_memory_rows,
    save_replacement_history,
    save_task_feedback_rows,
    upsert_draft_segment_feedback,
    update_managed_job,
    update_managed_source,
    update_monitor_state,
    update_source_snapshot,
    upsert_card_weight_profile,
    record_flashcard_pipeline_run,
    latest_flashcard_pipeline_run,
    upsert_intelligence_cards,
    upsert_knowledge_feedback,
    upsert_knowledge_state,
)
from agent_chappie.observation_engine import (
    ENTITY_NOISE_WORDS,
    SourcePackage,
    build_source_hash,
    clean_entity,
    clause_matches_keyword,
    deduplicate_observations,
    extract_action_detail,
    extract_clauses,
    extract_labeled_field,
    extract_named_entities,
    extract_observations,
    extract_signal_phrase,
    fetch_url_text,
    generate_recommended_tasks,
    host_to_entity,
    humanize_region,
    is_legal_or_evidentiary_context,
    is_non_commercial_research_context,
    normalize_source_package,
    recover_source_context,
    repair_recommended_tasks,
    utc_now_iso,
)


def _word_boundary_any(lowered: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(w)}\b", lowered) for w in words)


def _commercial_offer_tokens_in_text(lowered: str) -> bool:
    """True for B2B-style offer language; false for 'offering screenings' in research/clinical copy."""
    if is_non_commercial_research_context(lowered):
        return False
    if is_legal_or_evidentiary_context(lowered):
        return False
    if re.search(r"\b(offers?|offering)\b", lowered):
        return True
    if _word_boundary_any(lowered, ("discount", "voucher")):
        return True
    if "free onboarding" in lowered:
        return True
    if re.search(r"\btrial\b", lowered) and not re.search(r"\bclinical\s+trial\b", lowered):
        if re.search(
            r"\b(jury|bench|criminal|civil|appellate|mistrial|retrial|speedy)\s+trial\b",
            lowered,
        ) or re.search(r"\btrial\s+(court|attorney|lawyer|judge|date|hearing|day)\b", lowered):
            return False
        return True
    if _word_boundary_any(lowered, ("scholarship",)):
        return True
    return False


def _commercial_pricing_tokens_in_text(lowered: str) -> bool:
    if is_non_commercial_research_context(lowered):
        return False
    if _word_boundary_any(lowered, ("price", "pricing", "package", "bundle", "margin", "cost", "revenue")):
        return True
    if _word_boundary_any(lowered, ("onboarding",)) and "patient" not in lowered:
        return True
    return False
from agent_chappie.validation import (
    ValidationError,
    validate_job_request,
    validate_job_result,
    _validate_task_quality,
)


@dataclass
class WorkerBridgeConfig:
    host: str = "127.0.0.1"
    port: int = 9999
    shared_secret: str = "change-me"
    queue_dir: str = "runtime_status/observation_queue"
    local_db_path: str = "runtime_status/agent_brain.sqlite3"
    poll_interval_seconds: int = 60
    auto_research_enabled: bool = False


def load_config() -> WorkerBridgeConfig:
    return WorkerBridgeConfig(
        host=os.environ.get("AGENT_WORKER_HOST", "127.0.0.1"),
        port=int(os.environ.get("AGENT_WORKER_PORT", "8787")),
        shared_secret=os.environ.get("AGENT_SHARED_SECRET", "change-me"),
        queue_dir=os.environ.get("AGENT_OBSERVATION_QUEUE_DIR", "runtime_status/observation_queue"),
        local_db_path=os.environ.get("AGENT_LOCAL_DB_PATH", "runtime_status/agent_brain.sqlite3"),
        poll_interval_seconds=int(os.environ.get("AGENT_OBSERVATION_POLL_SECONDS", "60")),
        auto_research_enabled=os.environ.get("AGENT_AUTO_RESEARCH_ENABLED", "1") == "1",
    )


def _avoid_intel_card_pattern_keys(project_id: str, db_path: str) -> set[str]:
    return {
        str(r["pattern_key"])
        for r in list_generation_memory_rows(project_id, limit=200, path=db_path)
        if str(r.get("memory_kind") or "") == "avoid_intel_card" and float(r.get("weight") or 0) >= 0.35
    }


def _avoid_intel_card_copy_patterns(project_id: str, db_path: str) -> list[str]:
    """Normalized titles from intelligence delete_and_teach (parity with task avoid_title)."""
    return [
        str(r["pattern_key"])
        for r in list_generation_memory_rows(project_id, limit=200, path=db_path)
        if str(r.get("memory_kind") or "") == "avoid_title"
        and str(r.get("memory_id") or "").startswith("avoid_title_intel::")
        and float(r.get("weight") or 0) >= 0.35
    ]


def _intel_card_suppressed_by_teach(
    card: dict[str, Any],
    avoid: set[str],
    avoid_copy_patterns: list[str] | None = None,
) -> bool:
    if avoid:
        cid = str(card.get("card_id") or "")
        if ":heuristic:" in cid:
            if cid.split(":heuristic:", 1)[-1] in avoid:
                return True
        seg = str(card.get("segment") or "")
        if f"segment:{seg}" in avoid:
            return True
    if avoid_copy_patterns:
        fp = intel_card_text_fingerprint(
            card.get("insight"),
            card.get("implication"),
            card.get("potential_moves"),
        )
        nk = normalize_task_key(fp)
        if nk:
            for pk in avoid_copy_patterns:
                if avoid_title_pattern_matches(nk, pk):
                    return True
    return False


def create_server(config: WorkerBridgeConfig) -> ThreadingHTTPServer:
    queue_dir = Path(config.queue_dir)
    queue_dir.mkdir(parents=True, exist_ok=True)
    initialize_local_store(config.local_db_path)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._send_json(HTTPStatus.OK, {"status": "ok", "bridge": "worker"})
                return
            if self.path.startswith("/projects/") and self.path.endswith("/workspace"):
                if self.headers.get("x-agent-shared-secret") != config.shared_secret:
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return
                parts = self.path.strip("/").split("/")
                if len(parts) == 3:
                    project_id = parts[1]
                    self._send_json(HTTPStatus.OK, build_workspace_payload(project_id, config))
                    return
                if len(parts) == 3 and parts[2] == "sources":
                    project_id = parts[1]
                    self._send_json(HTTPStatus.OK, {"sources": list_managed_sources(project_id, path=config.local_db_path)})
                    return
                if len(parts) == 3 and parts[2] == "jobs":
                    project_id = parts[1]
                    self._send_json(HTTPStatus.OK, {"jobs": list_managed_jobs(project_id, path=config.local_db_path)})
                    return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.headers.get("x-agent-shared-secret") != config.shared_secret:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return

            if self.path == "/jobs":
                try:
                    content_length = int(self.headers.get("content-length", "0"))
                    payload = json.loads(self.rfile.read(content_length))
                    response = process_job_payload(payload, config)
                    self._send_json(HTTPStatus.OK, response)
                except Exception as exc:  # noqa: BLE001
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "worker_job_failed", "detail": str(exc)},
                    )
                return

            if self.path.startswith("/projects/"):
                try:
                    content_length = int(self.headers.get("content-length", "0"))
                    raw = self.rfile.read(content_length) if content_length else b"{}"
                    payload = json.loads(raw or b"{}")
                    response, status = process_management_request(self.command, self.path, payload, config)
                    self._send_json(status, response)
                except Exception as exc:  # noqa: BLE001
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "worker_management_failed", "detail": str(exc)},
                    )
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_PATCH(self) -> None:  # noqa: N802
            self.do_POST()

        def do_DELETE(self) -> None:  # noqa: N802
            self.do_POST()

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    return ThreadingHTTPServer((config.host, config.port), Handler)


def process_job_payload(payload: dict[str, Any], config: WorkerBridgeConfig) -> dict[str, Any]:
    job_request = validate_job_request(payload["job_request"])
    source_package = SourcePackage(
        project_id=job_request["project_id"],
        source_kind=payload["source_package"]["source_kind"],
        project_summary=payload["source_package"]["project_summary"],
        raw_text=payload["source_package"]["raw_text"],
        source_ref=payload["source_package"]["source_ref"],
        competitor=payload["source_package"].get("competitor"),
        region=payload["source_package"].get("region"),
        file_name=payload["source_package"].get("file_name"),
        content_type=payload["source_package"].get("content_type"),
        content_base64=payload["source_package"].get("content_base64"),
    )
    source_rows = list_recent_source_snapshots(job_request["project_id"], path=config.local_db_path)
    knowledge_rows = fetch_knowledge_rows(job_request["project_id"], path=config.local_db_path)
    source_package = recover_source_context(source_package, knowledge_rows, source_rows)
    source_package = normalize_source_package(source_package)

    enqueue_source_package(source_package, config)
    observations = sync_observations_for_source(source_package, config)
    enrich_project_with_auto_research(source_package, config)
    refreshed_sources = list_recent_source_snapshots(source_package.project_id, path=config.local_db_path)
    refreshed_knowledge = fetch_knowledge_rows(source_package.project_id, path=config.local_db_path)
    aggregated = list_recent_observations(source_package.project_id, path=config.local_db_path)
    fact_chips = build_fact_chips(refreshed_sources, aggregated or observations, refreshed_knowledge)
    atomic_facts = build_atomic_facts(
        source_package.project_id,
        refreshed_sources,
        aggregated or observations,
        refreshed_knowledge,
    )
    replace_atomic_facts(source_package.project_id, atomic_facts, path=config.local_db_path)
    evidence_units = build_evidence_units(source_package.project_id, refreshed_sources, aggregated or observations, fact_chips)
    replace_evidence_units(source_package.project_id, evidence_units, path=config.local_db_path)
    feedback_rows = list_task_feedback_rows(source_package.project_id, path=config.local_db_path)
    weight_profile = apply_adaptive_weight_profile(source_package.project_id, feedback_rows, config)
    candidate_cards: list[dict[str, Any]]
    card_scores: list[dict[str, Any]]
    job_id = str(job_request.get("job_id") or "")
    trinity_on = False
    trinity_wr = None
    try:
        from agent_chappie.flashcard_trinity.worker_integration import (
            TrinityWorkerResult,
            heuristic_flashcards_allowed,
            mlx_trinity_enabled,
            try_mlx_trinity_cards,
        )

        trinity_on = mlx_trinity_enabled()
        trinity_wr = try_mlx_trinity_cards(
            source_package.project_id,
            source_package,
            atomic_facts,
            refreshed_sources,
            weight_profile,
            job_id=job_id,
        )
    except Exception as exc:
        from agent_chappie.flashcard_trinity.worker_integration import (
            TrinityWorkerResult,
            mlx_trinity_enabled,
        )

        trinity_on = mlx_trinity_enabled()
        if trinity_on:
            trinity_wr = TrinityWorkerResult(
                [],
                [],
                False,
                {"outcome": "worker_bridge_exception", "error": str(exc)},
            )
        else:
            trinity_wr = None
    trinity_strict_block = False
    if trinity_wr is None:
        candidate_cards = build_flashcards_from_atomic_facts(
            source_package.project_id,
            atomic_facts,
            refreshed_sources,
            source_package.project_summary,
        )
        card_scores = score_flashcards(source_package.project_id, candidate_cards, atomic_facts, weight_profile)
        if job_id:
            record_flashcard_pipeline_run(
                job_id,
                source_package.project_id,
                "trinity_disabled",
                detail={"outcome": "disabled"},
                path=config.local_db_path,
            )
    elif trinity_wr.used_trinity_cards:
        candidate_cards, card_scores = trinity_wr.cards, trinity_wr.scores
        if job_id:
            record_flashcard_pipeline_run(
                job_id,
                source_package.project_id,
                "trinity",
                detail=trinity_wr.detail,
                path=config.local_db_path,
            )
    else:
        from agent_chappie.flashcard_trinity.worker_integration import heuristic_flashcards_allowed

        if trinity_on and not heuristic_flashcards_allowed():
            candidate_cards = []
            card_scores = []
            trinity_strict_block = True
            if job_id:
                record_flashcard_pipeline_run(
                    job_id,
                    source_package.project_id,
                    "trinity_strict_blocked",
                    reason=str(trinity_wr.detail.get("outcome", "")),
                    detail=trinity_wr.detail,
                    path=config.local_db_path,
                )
        else:
            candidate_cards = build_flashcards_from_atomic_facts(
                source_package.project_id,
                atomic_facts,
                refreshed_sources,
                source_package.project_summary,
            )
            card_scores = score_flashcards(source_package.project_id, candidate_cards, atomic_facts, weight_profile)
            if job_id:
                record_flashcard_pipeline_run(
                    job_id,
                    source_package.project_id,
                    "heuristic_fallback",
                    reason=str(trinity_wr.detail.get("outcome", "")),
                    detail=trinity_wr.detail,
                    path=config.local_db_path,
                )
    avoid_intel = _avoid_intel_card_pattern_keys(source_package.project_id, config.local_db_path)
    avoid_intel_copy = _avoid_intel_card_copy_patterns(source_package.project_id, config.local_db_path)
    candidate_cards = [
        c for c in candidate_cards if not _intel_card_suppressed_by_teach(c, avoid_intel, avoid_intel_copy)
    ]
    all_cards, visible_cards = apply_visibility_top_percent(candidate_cards, card_scores, percent=0.20)
    upsert_intelligence_cards(source_package.project_id, all_cards, card_scores, path=config.local_db_path)
    knowledge_cards = build_knowledge_cards(
        refreshed_sources,
        aggregated or observations,
        refreshed_knowledge,
        fetch_knowledge_feedback_rows(source_package.project_id, path=config.local_db_path),
        fact_chips,
        evidence_units,
    )
    draft_segments = build_draft_segments(
        source_package.project_id,
        refreshed_sources,
        aggregated or observations,
        knowledge_cards,
        fact_chips,
        evidence_units,
    )
    replace_draft_segments(source_package.project_id, draft_segments, path=config.local_db_path)
    generation_memory_rows = list_generation_memory_rows(source_package.project_id, path=config.local_db_path)
    result_payload = generate_learning_checklist(
        source_package,
        aggregated or observations,
        draft_segments,
        knowledge_cards,
        fact_chips,
        evidence_units,
        feedback_rows,
        generation_memory_rows,
    )
    # NBA derives from ranked intelligence cards (full scored corpus), materialized with the same
    # segment→task engine as the checklist so validation, execution steps, and judge enrichment align.
    nba_tasks = build_nba_tasks_from_intelligence_cards(
        all_cards,
        top_n=3,
        source_package=source_package,
        observations=aggregated or observations,
        knowledge_cards=knowledge_cards,
        fact_chips=fact_chips,
        evidence_units=evidence_units,
        feedback_rows=feedback_rows,
        generation_memory_rows=generation_memory_rows,
    )
    if trinity_strict_block:
        oc = str(trinity_wr.detail.get("outcome", "")) if trinity_wr else ""
        result_payload = {
            "reason": (
                "Trinity is required (FLASHCARD_MLX_TRINITY) but produced no usable promoted flashcards; "
                "heuristic fallback is disabled. Set AGENT_ALLOW_HEURISTIC_FLASHCARDS=1 for development "
                f"or fix MLX/models. Last outcome: {oc}."
            ),
        }
    elif nba_tasks:
        nba_ok = True
        try:
            for _task in nba_tasks:
                _validate_task_quality(_task)
        except ValidationError:
            nba_ok = False
        if nba_ok:
            # If intel cards collapse into duplicate move buckets (e.g. all homepage/comparison copy),
            # prefer the segment checklist so operators still see pricing vs proof vs messaging variety.
            sample = nba_tasks[:3]
            distinct_buckets = {str(t.get("move_bucket") or task_move_bucket(t)) for t in sample}
            if len(sample) >= 3 and len(distinct_buckets) < 3:
                nba_ok = False
        if nba_ok:
            result_payload = {
                "summary": (
                    "Next actions were ranked from scored intelligence cards (Know More) and materialized with the "
                    "same segment task builder and judging rules as the standard checklist."
                ),
                "recommended_tasks": nba_tasks,
            }
    used_source_refs: set[str] = set()

    if trinity_strict_block:
        job_result = validate_job_result(
            {
                "job_id": job_request["job_id"],
                "app_id": job_request["app_id"],
                "project_id": job_request["project_id"],
                "status": "blocked",
                "completed_at": utc_now_iso(),
                "result_payload": result_payload,
            }
        )
    elif "recommended_tasks" in result_payload:
        result_document = {
            "job_id": job_request["job_id"],
            "app_id": job_request["app_id"],
            "project_id": job_request["project_id"],
            "status": "complete",
            "completed_at": utc_now_iso(),
            "result_payload": result_payload,
            "decision_summary": {"route": "proceed", "confidence": 0.82},
            "trace_run_id": f"worker-{job_request['job_id']}",
            "trace_refs": [observation["signal_id"] for observation in observations],
        }
        try:
            job_result = validate_job_result(result_document)
        except ValidationError:
            repaired_payload = repair_recommended_tasks(source_package, observations, result_payload)
            if repaired_payload is not None:
                result_document["result_payload"] = repaired_payload
                job_result = validate_job_result(result_document)
            else:
                job_result = validate_job_result(
                    {
                        "job_id": job_request["job_id"],
                        "app_id": job_request["app_id"],
                        "project_id": job_request["project_id"],
                        "status": "blocked",
                        "completed_at": utc_now_iso(),
                        "result_payload": {
                            "reason": "Insufficient high-quality evidence to publish three concrete tasks without placeholders.",
                        },
                    }
                )
        if job_result["status"] == "complete" and "recommended_tasks" in job_result["result_payload"]:
            evidence_refs = {
                evidence_ref
                for task in job_result["result_payload"]["recommended_tasks"]
                for evidence_ref in task["evidence_refs"]
            }
            observation_lookup = {observation["signal_id"]: observation for observation in aggregated or observations}
            used_source_refs = {
                observation_lookup[evidence_ref]["source_ref"]
                for evidence_ref in evidence_refs
                if evidence_ref in observation_lookup
            }
            save_project_active_checklist(
                source_package.project_id,
                job_request["job_id"],
                job_result["result_payload"]["recommended_tasks"],
                config.local_db_path,
            )
    processing_summary = (
        job_result["result_payload"].get("summary")
        if job_result["status"] == "complete" and isinstance(job_result["result_payload"], dict)
        else "Source processed"
    )
    linked_tasks_by_source = build_linked_tasks_by_source(job_result, aggregated or observations)
    source_insights = build_source_insights(
        list_recent_source_snapshots(source_package.project_id, path=config.local_db_path),
        knowledge_cards,
        linked_tasks_by_source,
        evidence_units,
    )
    update_source_snapshot(
        source_package.source_ref,
        {
            "status": "processed" if job_result["status"] == "complete" else "blocked",
            "processing_summary": processing_summary,
            "key_takeaway": source_insights.get(source_package.source_ref, {}).get("key_takeaway"),
            "business_impact": source_insights.get(source_package.source_ref, {}).get("business_impact"),
            "linked_task_titles_json": json.dumps(source_insights.get(source_package.source_ref, {}).get("linked_tasks", [])),
            "source_confidence": source_insights.get(source_package.source_ref, {}).get("confidence", 0.58),
            "signal_count": len(list_observations_for_source(source_package.project_id, source_package.source_ref, path=config.local_db_path)),
            "knowledge_count": sum(1 for card in knowledge_cards if source_package.source_ref in card["source_refs"]),
            "last_used_in_checklist": 1 if source_package.source_ref in used_source_refs else 0,
        },
        path=config.local_db_path,
    )

    return {
        "job_result": job_result,
        "observation_count": len(observations),
        "observation_refs": [observation["signal_id"] for observation in observations],
    }


def process_management_request(
    method: str,
    path: str,
    payload: dict[str, Any],
    config: WorkerBridgeConfig,
) -> tuple[dict[str, Any], HTTPStatus]:
    parts = [p for p in path.strip("/").split("/") if p]
    if len(parts) < 3 or parts[0] != "projects":
        return {"error": "not_found"}, HTTPStatus.NOT_FOUND

    project_id = parts[1]
    resource = parts[2]

    if resource == "sources":
        if method == "POST" and len(parts) == 3:
            create_managed_source(
                {
                    "source_id": payload["source_id"],
                    "project_id": project_id,
                    "label": payload["label"],
                    "source_kind": payload["source_kind"],
                    "content_text": payload["content_text"],
                    "repeat_interval": payload.get("repeat_interval", "never"),
                    "repeat_anchor_at": payload.get("repeat_anchor_at"),
                    "status": payload.get("status", "active"),
                },
                path=config.local_db_path,
            )
            return {"sources": list_managed_sources(project_id, path=config.local_db_path)}, HTTPStatus.OK
        if method == "PATCH" and len(parts) == 4:
            update_managed_source(parts[3], payload, path=config.local_db_path)
            return {"sources": list_managed_sources(project_id, path=config.local_db_path)}, HTTPStatus.OK
        if method == "DELETE" and len(parts) == 4:
            delete_managed_source(parts[3], path=config.local_db_path)
            return {"sources": list_managed_sources(project_id, path=config.local_db_path)}, HTTPStatus.OK
        if len(parts) == 5 and parts[3] == "ingested":
            source_ref = parts[4]
            if method == "PATCH":
                if payload.get("action") == "reprocess":
                    reprocess_source_snapshot(project_id, source_ref, config)
                    return build_workspace_payload(project_id, config), HTTPStatus.OK
                update_source_snapshot(
                    source_ref,
                    {
                        "display_label": payload.get("display_label"),
                        "status": payload.get("status"),
                    },
                    path=config.local_db_path,
                )
                return build_workspace_payload(project_id, config), HTTPStatus.OK
            if method == "DELETE":
                delete_source_snapshot(project_id, source_ref, path=config.local_db_path)
                upsert_knowledge_state(list_recent_observations(project_id, path=config.local_db_path), config.local_db_path)
                return build_workspace_payload(project_id, config), HTTPStatus.OK

    if resource == "jobs":
        if method == "POST" and len(parts) == 3:
            create_managed_job(
                {
                    "managed_job_id": payload["managed_job_id"],
                    "project_id": project_id,
                    "name": payload["name"],
                    "trigger_type": payload["trigger_type"],
                    "schedule_text": payload.get("schedule_text"),
                    "status": payload.get("status", "active"),
                    "source_id": payload.get("source_id"),
                    "last_runs": payload.get("last_runs", []),
                },
                path=config.local_db_path,
            )
            return {"jobs": list_managed_jobs(project_id, path=config.local_db_path)}, HTTPStatus.OK
        if method == "PATCH" and len(parts) == 4:
            update_managed_job(parts[3], payload, path=config.local_db_path)
            return {"jobs": list_managed_jobs(project_id, path=config.local_db_path)}, HTTPStatus.OK
        if method == "DELETE" and len(parts) == 4:
            delete_managed_job(parts[3], path=config.local_db_path)
            return {"jobs": list_managed_jobs(project_id, path=config.local_db_path)}, HTTPStatus.OK

    if resource == "knowledge" and method == "PATCH" and len(parts) == 4:
        upsert_knowledge_feedback(
            project_id=project_id,
            knowledge_id=parts[3],
            status=str(payload.get("status", "confirmed")),
            confidence_source=str(payload.get("confidence_source", "user_modified")),
            original_payload=payload.get("original_payload"),
            corrected_title=payload.get("corrected_title"),
            corrected_summary=payload.get("corrected_summary"),
            corrected_implication=payload.get("corrected_implication"),
            corrected_potential_moves=payload.get("corrected_potential_moves"),
            corrected_items=payload.get("corrected_items"),
            path=config.local_db_path,
        )
        return build_workspace_payload(project_id, config), HTTPStatus.OK
    if resource == "knowledge" and method == "DELETE" and len(parts) == 4:
        upsert_knowledge_feedback(
            project_id=project_id,
            knowledge_id=parts[3],
            status=str(payload.get("status", "deleted_silent")),
            confidence_source=str(payload.get("confidence_source", "user_modified")),
            original_payload=payload.get("original_payload"),
            corrected_implication=payload.get("reason"),
            path=config.local_db_path,
        )
        return build_workspace_payload(project_id, config), HTTPStatus.OK

    if resource == "draft-segments" and method == "DELETE" and len(parts) == 4:
        upsert_draft_segment_feedback(
            project_id=project_id,
            segment_id=parts[3],
            status=str(payload.get("status", "deleted_silent")),
            reason=str(payload.get("reason") or "") or None,
            original_payload=payload.get("original_payload"),
            path=config.local_db_path,
        )
        return build_workspace_payload(project_id, config), HTTPStatus.OK

    if resource == "task-feedback" and method == "POST" and len(parts) == 3:
        return process_task_feedback(project_id, payload, config), HTTPStatus.OK

    if resource == "tasks" and method == "POST" and len(parts) == 4 and parts[3] == "feedback":
        try:
            result = apply_task_feedback(payload, config)
            return result, HTTPStatus.OK
        except ValueError as exc:
            return {"error": "invalid_task_feedback", "detail": str(exc)}, HTTPStatus.BAD_REQUEST

    if resource == "checklist" and method == "POST" and len(parts) == 3:
        job_id = str(payload.get("job_id") or f"regenerated_{project_id}_{int(time.time() * 1000)}")
        app_id = str(payload.get("app_id") or "consultant_followup_web")
        result_document = regenerate_project_checklist(project_id, config, job_id=job_id, app_id=app_id)
        return {"job_result": result_document, "workspace": build_workspace_payload(project_id, config)}, HTTPStatus.OK

    # --- Generation Memory Management ---
    if resource == "generation-memory" and method == "GET" and len(parts) == 3:
        rows = list_generation_memory_rows(project_id, path=config.local_db_path)
        return {"generation_memory": rows, "count": len(rows)}, HTTPStatus.OK

    if resource == "generation-memory" and method == "DELETE" and len(parts) == 4:
        deleted = delete_generation_memory_row(
            memory_id=parts[3], project_id=project_id, path=config.local_db_path
        )
        return {
            "deleted": deleted,
            "memory_id": parts[3],
        }, (HTTPStatus.OK if deleted else HTTPStatus.NOT_FOUND)

    if resource == "generation-memory" and method == "DELETE" and len(parts) == 3:
        count = clear_generation_memory(project_id=project_id, path=config.local_db_path)
        return {"cleared": True, "rows_removed": count}, HTTPStatus.OK

    # --- Held Tasks Management ---
    if resource == "held-tasks" and method == "GET" and len(parts) == 3:
        tasks = list_held_tasks(project_id=project_id, path=config.local_db_path)
        return {"held_tasks": tasks, "count": len(tasks)}, HTTPStatus.OK

    if resource == "held-tasks" and method == "POST" and len(parts) == 4 and parts[3] == "restore":
        # POST /projects/{id}/held-tasks/{held_task_id}/restore
        held_task_id = payload.get("held_task_id") or (parts[3] if len(parts) > 4 else "")
        restored = restore_held_task(
            held_task_id=str(held_task_id),
            project_id=project_id,
            path=config.local_db_path,
        )
        return {"restored": restored}, (HTTPStatus.OK if restored else HTTPStatus.NOT_FOUND)

    return {"error": "not_found"}, HTTPStatus.NOT_FOUND


def enqueue_source_package(source: SourcePackage, config: WorkerBridgeConfig) -> None:
    path = Path(config.queue_dir) / f"{int(time.time() * 1000)}_{source.project_id}.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(source.__dict__, handle, indent=2)


def sync_observations_for_source(source: SourcePackage, config: WorkerBridgeConfig) -> list[dict[str, Any]]:
    source_hash = build_source_hash(source)
    save_source_snapshot(source.__dict__, source_hash, config.local_db_path)
    extracted = extract_observations(source)
    existing = list_recent_observations(source.project_id, path=config.local_db_path)
    deduped = deduplicate_observations(extracted, existing)
    insert_observations(source.project_id, deduped, config.local_db_path)
    aggregated = list_recent_observations(source.project_id, path=config.local_db_path)
    upsert_knowledge_state(aggregated[:200], config.local_db_path)
    update_source_snapshot(
        source.source_ref,
        {
            "competitor": source.competitor,
            "region": source.region,
        },
        path=config.local_db_path,
    )
    update_monitor_state(
        "continuous_observation_loop",
        "processed",
        last_source_ref=source.source_ref,
        details={"project_id": source.project_id, "inserted_signals": len(deduped)},
        path=config.local_db_path,
    )
    return deduped


def enrich_project_with_auto_research(source: SourcePackage, config: WorkerBridgeConfig) -> None:
    if not config.auto_research_enabled:
        return
    if source.source_kind in {"url", "auto_research_url"}:
        return

    existing_sources = list_recent_source_snapshots(source.project_id, limit=40, path=config.local_db_path)
    existing_hashes = {row.get("source_hash") for row in existing_sources if row.get("source_hash")}
    for auto_source in build_auto_research_sources(source, existing_sources):
        source_hash = build_source_hash(auto_source)
        if source_hash in existing_hashes:
            continue
        try:
            sync_observations_for_source(auto_source, config)
        except Exception:
            continue


def build_auto_research_sources(
    source: SourcePackage,
    existing_sources: list[dict[str, Any]],
) -> list[SourcePackage]:
    competitors = []
    if source.competitor and clean_entity(source.competitor):
        competitors.append(normalize_research_entity(clean_entity(source.competitor) or ""))
    for entity in extract_named_entities(source.raw_text):
        cleaned = clean_entity(entity)
        if cleaned and cleaned not in competitors:
            normalized = normalize_research_entity(cleaned)
            if normalized and normalized not in competitors:
                competitors.append(normalized)
    competitors = [name for name in competitors if len(name) >= 3][:2]
    if not competitors:
        return []

    existing_urls = {
        extract_labeled_field(str(row.get("raw_text") or ""), "Source URL")
        for row in existing_sources
    }
    existing_urls = {url for url in existing_urls if url}
    market_terms = extract_market_terms(source)
    packages: list[SourcePackage] = []
    seen_urls: set[str] = set()
    query_suffixes = ("pricing", "trial", "testimonials")

    for competitor in competitors:
        for suffix in query_suffixes:
            for url in search_public_web_urls(f"{competitor} {suffix}", max_results=2):
                if url in seen_urls or url in existing_urls:
                    continue
                seen_urls.add(url)
                try:
                    fetched = fetch_url_text(url)
                except Exception:
                    continue
                if len(fetched.get("content", "").strip()) < 220:
                    continue
                if not is_relevant_auto_research_result(
                    competitor=competitor,
                    source=source,
                    url=url,
                    fetched=fetched,
                    market_terms=market_terms,
                ):
                    continue
                digest = build_source_hash(
                    SourcePackage(
                        project_id=source.project_id,
                        source_kind="auto_research_url",
                        project_summary=source.project_summary,
                        raw_text=fetched["content"],
                        source_ref=f"auto_source_{source.project_id}",
                        competitor=competitor,
                        region=source.region,
                        file_name=fetched.get("title"),
                    )
                )[:12]
                packages.append(
                    SourcePackage(
                        project_id=source.project_id,
                        source_kind="auto_research_url",
                        project_summary=source.project_summary,
                        raw_text=format_auto_research_source(url, fetched.get("title", competitor), fetched.get("content", "")),
                        source_ref=f"auto_source_{digest}",
                        competitor=competitor,
                        region=source.region,
                        file_name=fetched.get("title") or f"{competitor} web source",
                    )
                )
                break
            if len(packages) >= 3:
                return packages
    return packages


def normalize_research_entity(value: str) -> str:
    candidate = " ".join((value or "").split()).strip()
    if not candidate:
        return ""
    candidate = re.sub(
        r"\b(Focus|Analysis|Market|Intelligence|Report|Guide|Study|Platform|Software)\b$",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip(" -,:;")
    return clean_entity(candidate) or candidate


def extract_market_terms(source: SourcePackage) -> set[str]:
    text = " ".join(
        part
        for part in (
            source.project_summary or "",
            source.file_name or "",
            source.raw_text or "",
        )
        if part
    ).lower()
    allowlist = {
        "marketing",
        "seo",
        "search",
        "analytics",
        "intelligence",
        "agency",
        "pricing",
        "trial",
        "offer",
        "onboarding",
        "integration",
        "testimonial",
        "proof",
        "buyer",
        "buyers",
        "campaign",
        "conversion",
        "software",
        "saas",
        "operator",
    }
    return {term for term in allowlist if term in text}


def is_relevant_auto_research_result(
    *,
    competitor: str,
    source: SourcePackage,
    url: str,
    fetched: dict[str, str],
    market_terms: set[str],
) -> bool:
    title = str(fetched.get("title") or "")
    content = str(fetched.get("content") or "")
    haystack = f"{title} {content}".lower()
    host = urllib.parse.urlparse(url).netloc.lower()
    competitor_lc = (competitor or "").lower()
    competitor_tokens = [token for token in re.findall(r"[a-z0-9]+", competitor_lc) if len(token) >= 3]
    matched_competitor_tokens = sum(1 for token in competitor_tokens if token in haystack or token in host)
    host_entity = host_to_entity(host)
    host_entity_lc = (host_entity or "").lower()

    if matched_competitor_tokens == 0 and competitor_lc not in host_entity_lc:
        return False

    bad_host_terms = {"oncology", "pharma", "medical", "hospital", "clinical"}
    if any(term in host for term in bad_host_terms):
        return False

    bad_domain_terms = {
        "oncology",
        "cancer",
        "tumor",
        "gastric",
        "pharma",
        "clinical",
        "patient",
        "hospital",
        "treatment",
        "trial results",
        "medical",
        "bemarituzumab",
    }
    if any(term in haystack for term in bad_domain_terms):
        if not market_terms or sum(1 for term in market_terms if term in haystack) < 2:
            return False

    matched_market_terms = sum(1 for term in market_terms if term in haystack)
    if market_terms and matched_market_terms == 0:
        return False
    if market_terms and matched_market_terms < 2 and any(term in haystack for term in bad_domain_terms):
        return False

    competitor_root = competitor_tokens[0] if competitor_tokens else competitor_lc
    official_domain_hint = competitor_root.replace(" ", "")
    if official_domain_hint and official_domain_hint in host:
        return True

    if matched_competitor_tokens >= 2:
        return True
    if matched_competitor_tokens >= 1 and matched_market_terms >= 2:
        return True
    if matched_competitor_tokens >= 1 and source.source_kind == "url":
        return True
    return False


def search_public_web_urls(query: str, max_results: int = 3) -> list[str]:
    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
    request = urllib.request.Request(
        search_url,
        headers={
            "User-Agent": "Agent.Chappie/1.0 (+https://agent-chappie.vercel.app)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        html = response.read().decode("utf-8", errors="replace")

    urls: list[str] = []
    for encoded in re.findall(r"uddg=([^&\"]+)", html):
        url = urllib.parse.unquote(encoded)
        if url.startswith("http") and "duckduckgo.com" not in urllib.parse.urlparse(url).netloc:
            urls.append(url)
    for raw in re.findall(r'href=\"(https?://[^\"#]+)\"', html):
        if "duckduckgo.com" in urllib.parse.urlparse(raw).netloc:
            continue
        urls.append(raw)

    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        normalized = url.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(url)
        if len(deduped) >= max_results:
            break
    return deduped


def format_auto_research_source(url: str, title: str, content: str) -> str:
    return "\n".join(
        [
            f"Auto Research URL: {url}",
            f"Auto Research Title: {title}",
            f"Auto Research Content: {content}",
        ]
    )


def build_workspace_payload(project_id: str, config: WorkerBridgeConfig) -> dict[str, Any]:
    source_rows = list_recent_source_snapshots(project_id, path=config.local_db_path)
    observation_rows = list_recent_observations(project_id, path=config.local_db_path)
    knowledge_rows = fetch_knowledge_rows(project_id, path=config.local_db_path)
    knowledge_feedback_rows = fetch_knowledge_feedback_rows(project_id, path=config.local_db_path)
    draft_segment_feedback_rows = list_draft_segment_feedback_rows(project_id, path=config.local_db_path)
    monitor_rows = list_monitor_rows(path=config.local_db_path)
    fact_chips = build_fact_chips(source_rows, observation_rows, knowledge_rows)
    intelligence_cards = list_intelligence_cards(project_id, include_hidden=True, path=config.local_db_path)
    visible_intelligence_cards = [card for card in intelligence_cards if card.get("state") == "active"]
    evidence_units = build_evidence_units(project_id, source_rows, observation_rows, fact_chips)
    replace_evidence_units(project_id, evidence_units, path=config.local_db_path)
    knowledge_cards = build_knowledge_cards(source_rows, observation_rows, knowledge_rows, knowledge_feedback_rows, fact_chips, evidence_units)
    if source_rows or observation_rows or knowledge_cards or fact_chips:
        draft_segments = build_draft_segments(
            project_id,
            source_rows,
            observation_rows,
            knowledge_cards,
            fact_chips,
            evidence_units,
        )
        replace_draft_segments(project_id, draft_segments, path=config.local_db_path)
    else:
        draft_segments = list_draft_segments(project_id, path=config.local_db_path)
        draft_segments = [normalize_legacy_product_voice_in_segment(segment) for segment in draft_segments]
    draft_segments = apply_draft_segment_feedback(draft_segments, draft_segment_feedback_rows)
    draft_segments = append_held_knowledge_segments(draft_segments, knowledge_feedback_rows)
    source_cards = build_ingested_source_cards(source_rows, observation_rows, knowledge_cards, evidence_units)
    competitive_snapshot = build_competitive_snapshot(knowledge_cards, observation_rows, knowledge_rows, evidence_units)

    knowledge_summary_rows = [
        {
            "competitor": row["competitor"],
            "region": row["region"],
            "latest_observed_at": row["latest_observed_at"],
        }
        for row in knowledge_rows[:8]
        if clean_entity(row["competitor"])
    ]

    return {
        "project_id": project_id,
        "recent_sources": [
            {
                "source_ref": row["source_ref"],
                "source_kind": row["source_kind"],
                "created_at": row["created_at"],
                "preview": row["raw_text"][:220],
            }
            for row in source_rows[:5]
        ],
        "recent_activity": [
            {
                "signal_id": row["signal_id"],
                "signal_type": row["signal_type"],
                "summary": row["summary"],
                "observed_at": row["observed_at"],
                "source_ref": row["source_ref"],
            }
            for row in observation_rows[:6]
        ],
        "market_summary": {
            "pricing_changes": sum(1 for row in observation_rows if row["signal_type"] == "pricing_change"),
            "closure_signals": sum(1 for row in observation_rows if row["signal_type"] == "closure"),
            "offer_signals": sum(1 for row in observation_rows if row["signal_type"] in {"offer", "asset_sale"}),
        },
        "fact_chips": fact_chips,
        "intelligence_cards": intelligence_cards,
        "visible_intelligence_cards": visible_intelligence_cards,
        "latest_flashcard_pipeline_run": latest_flashcard_pipeline_run(project_id, path=config.local_db_path),
        "draft_segments": draft_segments,
        "competitive_snapshot": competitive_snapshot,
        "knowledge_summary": knowledge_summary_rows[:5],
        "monitor_jobs": [
            {
                "job_name": row["job_name"],
                "status": row["status"],
                "last_run_at": row["last_run_at"],
                "last_source_ref": row["last_source_ref"],
            }
            for row in monitor_rows[:5]
        ],
        "knowledge_cards": knowledge_cards,
        "source_cards": source_cards,
        "managed_sources": list_managed_sources(project_id, path=config.local_db_path),
        "managed_jobs": list_managed_jobs(project_id, path=config.local_db_path),
    }


FEEDBACK_V2_ACTION_TYPES = frozenset(
    {
        "done",
        "edit",
        "decline_and_replace",
        "delete_only",
        "delete_and_teach",
        "hold_for_later",
    }
)


def _map_v2_action_to_feedback_type(action_type: str) -> str:
    return {
        "done": "completed",
        "edit": "edited",
        "decline_and_replace": "declined",
        "delete_only": "deleted_silent",
        "delete_and_teach": "deleted_with_annotation",
        "hold_for_later": "held_for_later",
    }[action_type]


def _resolve_task_from_checklist(tasks: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    tid = str(task_id).strip()
    for entry in tasks:
        if str(entry.get("task_id") or "") == tid:
            return entry
        if str(entry.get("rank") or "") == tid:
            return entry
    if tid.isdigit():
        rank = int(tid)
        for entry in tasks:
            if int(entry.get("rank") or 0) == rank:
                return entry
        if 1 <= rank <= len(tasks):
            return tasks[rank - 1]
    return None


def apply_task_feedback(feedback_payload: dict[str, Any], config: WorkerBridgeConfig) -> dict[str, Any]:
    """
    feedback_v2 entrypoint: { project_id, task_id, action_type, comment?, edited_title? }
    Loads the active checklist from the worker DB (or bootstraps via regeneration), applies one action, returns exactly 3 tasks.
    """
    project_id = str(feedback_payload.get("project_id") or "").strip()
    task_id = str(feedback_payload.get("task_id") or "").strip()
    action_type = str(feedback_payload.get("action_type") or "").strip()
    comment = str(feedback_payload.get("comment") or "").strip()
    edited_title = str(feedback_payload.get("edited_title") or "").strip()
    if not project_id or not task_id or not action_type:
        raise ValueError("project_id, task_id, and action_type are required")
    if action_type not in FEEDBACK_V2_ACTION_TYPES:
        raise ValueError(f"Unsupported action_type: {action_type}")

    stored = get_project_active_checklist(project_id, path=config.local_db_path)
    if not stored or not stored.get("tasks"):
        job_id_boot = f"bootstrap_{project_id}_{int(time.time() * 1000)}"
        result_document = regenerate_project_checklist(
            project_id,
            config,
            job_id=job_id_boot,
            app_id="consultant_followup_web",
        )
        boot_tasks = result_document["result_payload"]["recommended_tasks"]
        save_project_active_checklist(project_id, job_id_boot, boot_tasks, config.local_db_path)
        current_tasks = boot_tasks
        job_id = job_id_boot
    else:
        current_tasks = stored["tasks"]
        job_id = stored["job_id"]

    target = _resolve_task_from_checklist(current_tasks, task_id)
    if not target:
        raise ValueError("task_id does not match the active checklist")

    internal_type = _map_v2_action_to_feedback_type(action_type)
    adjusted_text: str | None = None
    if action_type == "edit":
        adjusted_text = edited_title or comment or None
        if not adjusted_text:
            raise ValueError("edit requires edited_title or comment with new wording")

    feedback_item: dict[str, Any] = {
        "feedback_id": f"fb_v2_{project_id}_{int(time.time() * 1000)}",
        "task_id": target.get("rank"),
        "original_title": target["title"],
        "original_expected_advantage": target.get("expected_advantage"),
        "feedback_type": internal_type,
        "feedback_comment": comment or None,
        "adjusted_text": adjusted_text,
        "replacement_generated": True,
        "action_type": action_type,
    }
    inner_payload = {
        "job_id": job_id,
        "current_tasks": list(current_tasks),
        "task_feedback_items": [feedback_item],
    }
    result = process_task_feedback(project_id, inner_payload, config)
    out_tasks = result["job_result"]["result_payload"]["recommended_tasks"]
    return {
        "tasks": out_tasks,
        "job_id": job_id,
        "job_result": result["job_result"],
        "workspace": result.get("workspace"),
    }


def process_task_feedback(project_id: str, payload: dict[str, Any], config: WorkerBridgeConfig) -> dict[str, Any]:
    job_id = str(payload.get("job_id") or "")
    feedback_items = payload.get("task_feedback_items") or []
    current_tasks = payload.get("current_tasks") or []
    if not isinstance(feedback_items, list) or not feedback_items:
        raise ValueError("Task feedback requires at least one feedback item.")
    if not job_id:
        job_id = f"feedback_job_{project_id}_{int(time.time() * 1000)}"

    rows = []
    for index, item in enumerate(feedback_items):
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "feedback_id": str(item.get("feedback_id") or f"task_feedback_{project_id}_{index+1}_{int(time.time() * 1000)}"),
                "task_id": item.get("task_id") or item.get("rank"),
                "original_title": str(item.get("original_title") or ""),
                "original_expected_advantage": item.get("original_expected_advantage"),
                "feedback_type": str(item.get("feedback_type") or "commented"),
                "feedback_comment": item.get("feedback_comment"),
                "adjusted_text": item.get("adjusted_text"),
                "replacement_generated": True,
                "action_type": item.get("action_type"),
            }
        )
    save_task_feedback_rows(project_id, job_id, rows, path=config.local_db_path)
    # Only write to generation_memory for feedback types that carry intent signals.
    # delete_only (deleted_silent) and done (completed) must NOT write teaching memory.
    memory_eligible_rows = [
        row for row in rows
        if row["feedback_type"] not in {"deleted_silent", "completed"}
    ]
    if memory_eligible_rows:
        save_generation_memory_rows(project_id, build_generation_memory_rows(memory_eligible_rows), path=config.local_db_path)

    # Hold-for-later: save to held_tasks table
    for row in rows:
        if row["feedback_type"] == "held_for_later":
            save_held_task(
                project_id=project_id,
                held_task_id=str(row.get("feedback_id") or f"held_{project_id}_{int(time.time() * 1000)}"),
                title=str(row.get("original_title") or ""),
                rank=int(row["task_id"]) if row.get("task_id") and str(row.get("task_id")).isdigit() else None,
                path=config.local_db_path,
            )

    interacted_titles = {str(item.get("original_title") or "") for item in rows}
    retained_tasks = [task for task in current_tasks if task.get("title") not in interacted_titles]
    
    for item in rows:
        if item.get("feedback_type") == "edited":
            original_task = next((t for t in current_tasks if t.get("title") == item.get("original_title")), None)
            if original_task:
                edited_task = dict(original_task)
                edited_task["title"] = str(item.get("adjusted_text") or original_task.get("title") or "")
                retained_tasks.append(edited_task)

    result_document = regenerate_project_checklist(
        project_id,
        config,
        job_id=job_id,
        app_id="consultant_followup_web",
        confidence=0.74,
        retained_tasks=retained_tasks,
    )
    declined_rows = [
        row
        for row in rows
        if row["feedback_type"] in {"declined", "commented", "deleted_silent", "deleted_with_annotation", "held_for_later"}
    ]
    for row, task in zip(declined_rows, result_document["result_payload"]["recommended_tasks"], strict=False):
        save_replacement_history(
            project_id=project_id,
            prior_task_title=row["original_title"],
            replacement_title=task["title"],
            source_feedback_id=row["feedback_id"],
            path=config.local_db_path,
        )
    save_project_active_checklist(
        project_id,
        job_id,
        result_document["result_payload"]["recommended_tasks"],
        config.local_db_path,
    )
    return {"job_result": result_document, "workspace": build_workspace_payload(project_id, config)}


def regenerate_project_checklist(
    project_id: str,
    config: WorkerBridgeConfig,
    *,
    job_id: str,
    app_id: str,
    confidence: float = 0.78,
    retained_tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:

    source_rows = list_recent_source_snapshots(project_id, path=config.local_db_path)
    observation_rows = list_recent_observations(project_id, path=config.local_db_path)
    knowledge_rows = fetch_knowledge_rows(project_id, path=config.local_db_path)
    knowledge_feedback_rows = fetch_knowledge_feedback_rows(project_id, path=config.local_db_path)
    fact_chips = build_fact_chips(source_rows, observation_rows, knowledge_rows)
    evidence_units = list_evidence_units(project_id, path=config.local_db_path)
    if not evidence_units:
        evidence_units = build_evidence_units(project_id, source_rows, observation_rows, fact_chips)
        replace_evidence_units(project_id, evidence_units, path=config.local_db_path)
    knowledge_cards = build_knowledge_cards(source_rows, observation_rows, knowledge_rows, knowledge_feedback_rows, fact_chips, evidence_units)
    draft_segments = list_draft_segments(project_id, path=config.local_db_path)
    if not draft_segments:
        draft_segments = build_draft_segments(
            project_id,
            source_rows,
            observation_rows,
            knowledge_cards,
            fact_chips,
            evidence_units,
        )
        replace_draft_segments(project_id, draft_segments, path=config.local_db_path)

    seed_source = SourcePackage(
        project_id=project_id,
        source_kind=source_rows[0]["source_kind"] if source_rows else "manual_text",
        project_summary=source_rows[0]["project_summary"] if source_rows else "managed_on_worker",
        raw_text=source_rows[0]["raw_text"] if source_rows else "Feedback-driven regeneration",
        source_ref=source_rows[0]["source_ref"] if source_rows else f"feedback_source_{project_id}",
        competitor=source_rows[0].get("competitor") if source_rows else None,
        region=source_rows[0].get("region") if source_rows else None,
    )
    feedback_rows = list_task_feedback_rows(project_id, path=config.local_db_path)
    generation_memory_rows = list_generation_memory_rows(project_id, path=config.local_db_path)
    # Decay memory influence before each generation cycle
    if generation_memory_rows:
        decay_generation_memory(project_id, path=config.local_db_path)
        generation_memory_rows = list_generation_memory_rows(project_id, path=config.local_db_path)
    result_payload = generate_learning_checklist(
        seed_source,
        observation_rows,
        draft_segments,
        knowledge_cards,
        fact_chips,
        evidence_units,
        feedback_rows,
        generation_memory_rows,
        retained_tasks=retained_tasks,
    )
    result_document = validate_job_result(
        {
            "job_id": job_id,
            "app_id": app_id,
            "project_id": project_id,
            "status": "complete",
            "completed_at": utc_now_iso(),
            "result_payload": result_payload,
            "decision_summary": {"route": "proceed", "confidence": confidence},
        }
    )
    return result_document


def reprocess_source_snapshot(project_id: str, source_ref: str, config: WorkerBridgeConfig) -> None:
    snapshot = get_source_snapshot(project_id, source_ref, path=config.local_db_path)
    if not snapshot:
        raise ValueError("The ingested source could not be found.")
    source = SourcePackage(
        project_id=project_id,
        source_kind=snapshot["source_kind"],
        project_summary=snapshot["project_summary"],
        raw_text=snapshot["raw_text"],
        source_ref=snapshot["source_ref"],
        competitor=snapshot.get("competitor"),
        region=snapshot.get("region"),
        file_name=snapshot.get("display_label"),
    )
    normalized = normalize_source_package(source)
    observations = sync_observations_for_source(normalized, config)
    refreshed_sources = list_recent_source_snapshots(project_id, path=config.local_db_path)
    refreshed_observations = list_recent_observations(project_id, path=config.local_db_path)
    refreshed_knowledge = fetch_knowledge_rows(project_id, path=config.local_db_path)
    fact_chips = build_fact_chips(refreshed_sources, refreshed_observations, refreshed_knowledge)
    evidence_units = build_evidence_units(project_id, refreshed_sources, refreshed_observations, fact_chips)
    replace_evidence_units(project_id, evidence_units, path=config.local_db_path)
    knowledge_cards = build_knowledge_cards(
        refreshed_sources,
        refreshed_observations,
        refreshed_knowledge,
        fetch_knowledge_feedback_rows(project_id, path=config.local_db_path),
        fact_chips,
        evidence_units,
    )
    source_insights = build_source_insights(
        list_recent_source_snapshots(project_id, path=config.local_db_path),
        knowledge_cards,
        {},
        evidence_units,
    )
    update_source_snapshot(
        source_ref,
        {
            "status": "processed",
            "processing_summary": f"Processed {len(observations)} signals and {len(knowledge_cards)} knowledge cards",
            "key_takeaway": source_insights.get(source_ref, {}).get("key_takeaway"),
            "business_impact": source_insights.get(source_ref, {}).get("business_impact"),
            "linked_task_titles_json": json.dumps(source_insights.get(source_ref, {}).get("linked_tasks", [])),
            "source_confidence": source_insights.get(source_ref, {}).get("confidence", 0.58),
            "signal_count": len(list_observations_for_source(project_id, source_ref, path=config.local_db_path)),
            "knowledge_count": sum(1 for card in knowledge_cards if source_ref in card["source_refs"]),
        },
        path=config.local_db_path,
    )


def build_ingested_source_cards(
    source_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
    knowledge_cards: list[dict[str, Any]],
    evidence_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_cards: list[dict[str, Any]] = []
    for row in source_rows[:8]:
        signal_count = sum(1 for observation in observation_rows if observation["source_ref"] == row["source_ref"])
        knowledge_count = sum(1 for card in knowledge_cards if row["source_ref"] in card["source_refs"])
        source_cards.append(
            {
                "source_ref": row["source_ref"],
                "label": row.get("display_label") or row["source_ref"],
                "source_kind": row["source_kind"],
                "status": row.get("status") or "processed",
                "processing_summary": row.get("processing_summary") or (
                    f"Processed {signal_count} signals and {knowledge_count} knowledge cards"
                    if signal_count or knowledge_count
                    else "Source extracted and stored"
                ),
                "last_used_in_checklist": bool(row.get("last_used_in_checklist")),
                "signal_count": signal_count,
                "key_takeaway": row.get("key_takeaway") or derive_source_takeaway(row, knowledge_cards, evidence_units),
                "business_impact": row.get("business_impact") or derive_source_business_impact(row, knowledge_cards, evidence_units),
                "linked_tasks": parse_json_list(row.get("linked_task_titles_json")),
                "confidence": round(float(row.get("source_confidence") or derive_source_confidence(signal_count, knowledge_count)), 2),
                "created_at": row["created_at"],
                "preview": row["raw_text"][:220],
            }
        )
    return source_cards


def build_knowledge_cards(
    source_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
    knowledge_rows: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
    fact_chips: list[dict[str, Any]],
    evidence_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    def kb_plain_potential_moves(items: list[str]) -> list[str]:
        """Operator-facing suggestions only—no row[]= / source_ref= debug strings."""
        out: list[str] = []
        seen: set[str] = set()
        for item in items:
            raw = str(item).strip()
            if _looks_like_debug_potential_move_line(raw):
                raw = _strip_debug_potential_move_prefix(raw)
            c = _clip_task_copy(raw, 220)
            if not c:
                continue
            key = c.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
            if len(out) >= 3:
                return out
        for filler in (
            "Check this read against your live site and what prospects say on recent calls.",
            "If it is wrong, use Decline and teach so the system learns your market.",
            "Pick one concrete homepage or pricing tweak to test against this pattern.",
        ):
            if len(out) >= 3:
                break
            if filler.lower() not in seen:
                seen.add(filler.lower())
                out.append(filler)
        return out[:3]

    feedback_lookup = {row["knowledge_id"]: row for row in feedback_rows}
    entities = unique_entities(source_rows, observation_rows, knowledge_rows)
    cards: list[dict[str, Any]] = []
    facts_by_category = group_fact_chips(fact_chips)
    units_by_kind = group_evidence_units(evidence_units)
    all_units = sorted(evidence_units, key=lambda unit: float(unit.get("confidence") or 0), reverse=True)

    market_units = unique_units_by_label(
        units_by_kind.get("pricing", [])
        + units_by_kind.get("offer", [])
        + units_by_kind.get("positioning", [])
        + units_by_kind.get("proof", [])
        + units_by_kind.get("opportunity", [])
    )
    market_items = select_market_summary_items(market_units, source_rows)
    if not market_items and source_rows:
        market_items.append(f"{len(source_rows)} ingested source{'s' if len(source_rows) != 1 else ''} are shaping the current knowledge state.")
    if not market_items:
        topic_items = summarize_market_fact_patterns(fact_chips) or derive_topic_items(" ".join(row["raw_text"] for row in source_rows))
        market_items.extend(topic_items[:3])
    cards.append(
        knowledge_card(
            "market_summary",
            "Market Summary",
            "What the system currently knows about this market or project from the ingested sources.",
            market_items or ["No market synthesis has been derived yet."],
            market_summary_insight(market_units, source_rows),
            market_summary_implication(market_units),
            kb_plain_potential_moves(market_items or []),
            observation_rows[:4],
            flatten_unit_source_refs(market_units[:5]) or [row["source_ref"] for row in source_rows[:4]],
            0.78 if source_rows else 0.22,
            feedback_lookup,
            support_count=len(market_units),
            strongest_excerpt=strongest_unit_excerpt(market_units),
        )
    )

    competitor_items = competitor_card_items(evidence_units, facts_by_category.get("competitor", []), entities)
    competitor_source_refs = source_refs_for_competitor_items(competitor_items, evidence_units)
    cards.append(
        knowledge_card(
            "competitors_detected",
            "Competitors Detected",
            "Named companies, schools, clubs, or products we extracted from the current source set.",
            competitor_items[:6] or ["No named competitors have been extracted with enough confidence yet."],
            _clip_task_copy(
                (
                    f"We picked up {len(competitor_items)} named competitor candidate(s) from this material. "
                    f"Strongest signals: {', '.join(competitor_items[:4])}."
                )
                if competitor_items
                else "We did not extract confident named competitors from this pass—your sources may not name firms explicitly yet.",
                280,
            ),
            _clip_task_copy(
                "Treat this as a draft list to verify; wrong names create wrong tasks downstream."
                if competitor_items
                else "Add a memo, deck, or page that names who you actually compete with.",
                220,
            ),
            kb_plain_potential_moves(competitor_items[:6] or ["Name one or two competitors explicitly in your sources so we can track them."]),
            observation_rows[:4],
            competitor_source_refs or flatten_fact_source_refs(facts_by_category.get("competitor", [])) or [row["source_ref"] for row in source_rows[:4]],
            0.74 if competitor_items else 0.28,
            feedback_lookup,
            support_count=len(competitor_items),
            strongest_excerpt=strongest_competitor_excerpt(competitor_items, evidence_units),
        )
    )

    pricing_facts = facts_by_category.get("pricing", [])
    pricing_units = units_by_kind.get("pricing", []) + units_by_kind.get("pricing_packaging", [])
    used_item_signatures = {normalize_item_signature(item) for item in market_items}

    pricing_items = dedupe_card_items(
        action_aware_card_items(
        pricing_units,
        [unit["label"] for unit in pricing_units[:5]] or [fact["label"] for fact in pricing_facts],
        ),
        blocked_signatures=used_item_signatures,
    )
    used_item_signatures.update(normalize_item_signature(item) for item in pricing_items)
    cards.append(
        knowledge_card(
            "pricing_packaging",
            "Pricing / Packaging",
            "Commercial packaging and pricing observations we extracted from the current source material.",
            pricing_items[:5] or ["No pricing or packaging observations are strong enough yet."],
            _clip_task_copy(
                (
                    f"Pricing and packaging language shows up in {len(pricing_units)} evidence line(s) from this ingest."
                    if pricing_units
                    else "We did not isolate strong pricing or packaging claims in this pass."
                ),
                240,
            ),
            _clip_task_copy(
                "Buyers will compare numbers and packaging—make sure your story matches what they see in the wild."
                if pricing_units
                else "Upload or paste material that states fees, plans, or packaging more explicitly.",
                220,
            ),
            kb_plain_potential_moves(pricing_items[:5] or ["Add clearer pricing or packaging language if this card feels empty."]),
            [row for row in observation_rows if row["signal_type"] == "pricing_change"][:4],
            flatten_unit_source_refs(pricing_units[:5]) or flatten_fact_source_refs(pricing_facts[:5]) or source_refs_for_items(pricing_items[:5], source_rows),
            0.71 if pricing_items else 0.24,
            feedback_lookup,
            support_count=len(pricing_units),
            strongest_excerpt=strongest_unit_excerpt(pricing_units),
        )
    )

    positioning_facts = facts_by_category.get("offer", []) + facts_by_category.get("positioning", []) + facts_by_category.get("segment", [])
    positioning_units = units_by_kind.get("offer", []) + units_by_kind.get("positioning", []) + units_by_kind.get("segment", [])
    positioning_items = dedupe_card_items(
        action_aware_card_items(
        positioning_units,
        [unit["label"] for unit in positioning_units[:5]] or [fact["label"] for fact in positioning_facts],
        ),
        blocked_signatures=used_item_signatures,
    )
    used_item_signatures.update(normalize_item_signature(item) for item in positioning_items)
    cards.append(
        knowledge_card(
            "offer_positioning",
            "Offer / Positioning",
            "Offer language, positioning claims, and tactical market signals found in the sources.",
            positioning_items[:5] or ["No clear positioning or offer observations have been extracted yet."],
            _clip_task_copy(
                (
                    f"Offer and positioning cues appear across {len(positioning_units)} evidence snippet(s) here."
                    if positioning_units
                    else "We did not find strong offer or positioning lines in this ingest."
                ),
                240,
            ),
            _clip_task_copy(
                "This shapes how buyers frame you versus alternatives—teach the card if it misreads your story."
                if positioning_units
                else "Paste homepage, sales deck, or battlecard excerpts so we can read your positioning.",
                220,
            ),
            kb_plain_potential_moves(positioning_items[:5] or ["Add copy that states how you position against alternatives."]),
            [row for row in observation_rows if row["signal_type"] in {"offer", "messaging_shift"}][:4],
            flatten_unit_source_refs(positioning_units[:5]) or flatten_fact_source_refs(positioning_facts[:5]) or source_refs_for_items(positioning_items[:5], source_rows),
            0.73 if positioning_items else 0.25,
            feedback_lookup,
            support_count=len(positioning_units),
            strongest_excerpt=strongest_unit_excerpt(positioning_units),
        )
    )

    proof_facts = facts_by_category.get("proof", [])
    proof_units = units_by_kind.get("proof", [])
    proof_items = dedupe_card_items(
        action_aware_card_items(
        proof_units,
        [unit["label"] for unit in proof_units[:5]] or [fact["label"] for fact in proof_facts],
        ),
        blocked_signatures=used_item_signatures,
    )
    cards.append(
        knowledge_card(
            "proof_signals",
            "Proof Signals",
            "Trust cues, proof points, and credibility patterns extracted from the current source set.",
            proof_items[:5] or ["No proof signals have been extracted yet."],
            _clip_task_copy(
                (
                    f"We surfaced {len(proof_units)} proof- or trust-shaped snippet(s) from your sources."
                    if proof_units
                    else "No strong proof or trust cues stood out in this pass."
                ),
                240,
            ),
            _clip_task_copy(
                "Weak proof on your side will stand out if competitors lean on logos, quotes, or case studies."
                if proof_units
                else "Include customer stories, metrics, or third-party validation in the next upload.",
                220,
            ),
            kb_plain_potential_moves(proof_items[:5] or ["Add testimonials, logos, or case-study language if proof looks thin."]),
            [row for row in observation_rows if row["signal_type"] == "proof_signal"][:4],
            flatten_unit_source_refs(proof_units[:5]) or flatten_fact_source_refs(proof_facts[:5]) or source_refs_for_items(proof_items[:5], source_rows),
            0.69 if proof_items else 0.21,
            feedback_lookup,
            support_count=len(proof_units),
            strongest_excerpt=strongest_unit_excerpt(proof_units),
        )
    )

    open_questions = []
    if not any(row.get("region") and row["region"] != "region_unknown" for row in source_rows + knowledge_rows):
        open_questions.append("Geography is still fuzzy—add where you sell or compete so comparisons stay grounded.")
    if not competitor_items:
        open_questions.append("We still need clearer named competitors in the source material.")
    if source_rows and not any(
        unit["unit_kind"] in {"pricing", "pricing_change", "offer", "proof", "positioning", "messaging_shift", "proof_signal"}
        for unit in all_units
    ):
        open_questions.append("Commercial signals (pricing, offers, proof) are thin; richer sources will sharpen this workspace.")
    open_questions.extend(missing_evidence_categories(all_units)[:2])
    if not open_questions:
        open_questions.append("No major structural gaps jumped out on this pass.")
    cards.append(
        knowledge_card(
            "open_questions",
            "Open Questions",
            "Weak-confidence areas and unresolved questions the operator may want to confirm or correct.",
            open_questions,
            _clip_task_copy(
                f"We flagged {len(open_questions)} area(s) where your confirmation—or better sources—would tighten the read.",
                220,
            ),
            _clip_task_copy(
                "These are prompts, not verdicts: fix them with edits, new uploads, or Decline and teach when we misread you.",
                200,
            ),
            kb_plain_potential_moves(open_questions),
            observation_rows[:2],
            [row["source_ref"] for row in source_rows[:3]],
            0.55,
            feedback_lookup,
            support_count=len(open_questions),
        )
    )

    hidden_statuses = {"deleted", "deleted_silent", "deleted_with_annotation", "dismissed", "held", "held_for_later"}
    return [
        card
        for card in cards
        if feedback_lookup.get(card["knowledge_id"], {}).get("status") not in hidden_statuses
    ]


def append_held_knowledge_segments(
    draft_segments: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    held_statuses = {"held", "held_for_later"}
    held_segments: list[dict[str, Any]] = []
    existing_ids = {str(segment.get("segment_id") or "") for segment in draft_segments}
    for row in feedback_rows:
        if str(row.get("status") or "") not in held_statuses:
            continue
        knowledge_id = str(row.get("knowledge_id") or "").strip()
        if not knowledge_id:
            continue
        segment_id = f"held::{knowledge_id}"
        if segment_id in existing_ids:
            continue
        original_payload = row.get("original_payload") if isinstance(row.get("original_payload"), dict) else {}
        held_segments.append(
            {
                "segment_id": segment_id,
                "segment_kind": "held_knowledge",
                "title": str(row.get("corrected_title") or original_payload.get("title") or "Held knowledge card"),
                "segment_text": str(
                    row.get("corrected_summary")
                    or original_payload.get("summary")
                    or row.get("corrected_implication")
                    or original_payload.get("implication")
                    or "We parked this knowledge card so it does not drive the live surface right now."
                ),
                "source_refs": [],
                "evidence_refs": [f"knowledge::{knowledge_id}"],
                "importance": 0.41,
                "confidence": 0.66,
                "updated_at": row.get("updated_at"),
            }
        )
        existing_ids.add(segment_id)
    return draft_segments + held_segments


def apply_draft_segment_feedback(
    draft_segments: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hidden_statuses = {"deleted", "deleted_silent", "deleted_with_annotation", "held", "held_for_later"}
    hidden_ids = {
        str(row.get("segment_id") or "")
        for row in feedback_rows
        if str(row.get("status") or "") in hidden_statuses
    }
    if not hidden_ids:
        return draft_segments
    return [segment for segment in draft_segments if str(segment.get("segment_id") or "") not in hidden_ids]


def build_draft_segments(
    project_id: str,
    source_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
    knowledge_cards: list[dict[str, Any]],
    fact_chips: list[dict[str, Any]],
    evidence_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_segment(
        segment_id: str,
        segment_kind: str,
        title: str,
        segment_text: str,
        source_refs: list[str],
        evidence_refs: list[str],
        importance: float,
        confidence: float,
    ) -> None:
        key = f"{segment_kind}|{title}|{segment_text}".lower()
        if key in seen:
            return
        seen.add(key)
        namespaced_segment_id = f"{project_id}::{segment_id}"
        segments.append(
            {
                "segment_id": namespaced_segment_id,
                "segment_kind": segment_kind,
                "title": title,
                "segment_text": segment_text,
                "source_refs": unique_values(source_refs),
                "evidence_refs": unique_values(evidence_refs),
                "importance": round(float(importance), 2),
                "confidence": round(float(confidence), 2),
            }
        )

    for cluster_segment in build_unit_cluster_segments(project_id=project_id, evidence_units=evidence_units)[:16]:
        add_segment(
            cluster_segment["segment_id"],
            cluster_segment["segment_kind"],
            cluster_segment["title"],
            cluster_segment["segment_text"],
            cluster_segment["source_refs"],
            cluster_segment["evidence_refs"],
            cluster_segment["importance"],
            cluster_segment["confidence"],
        )

    for card in knowledge_cards:
        primary_trigger = (
            str(card.get("strongest_excerpt") or "").strip()
            or (str(card["items"][0]).strip() if card.get("items") else "")
            or f"{card['insight']} {card['implication']}"
        )
        add_segment(
            f"segment:{card['knowledge_id']}",
            card["knowledge_id"],
            card["title"],
            normalize_legacy_product_voice(primary_trigger),
            card.get("source_refs", []),
            card.get("evidence_refs", []),
            min(0.99, 0.45 + float(card["confidence"])),
            float(card["confidence"]),
        )
        for index, item in enumerate(card.get("items", [])[:5]):
            add_segment(
                f"segment:{card['knowledge_id']}:{index + 1}",
                card["knowledge_id"],
                card["title"],
                normalize_legacy_product_voice(item),
                card.get("source_refs", []),
                card.get("evidence_refs", []),
                min(0.95, 0.38 + float(card["confidence"])),
                float(card["confidence"]),
            )

    for chip in fact_chips:
        add_segment(
            f"fact:{chip['fact_id']}",
            str(chip["category"]),
            humanize_fact_category(str(chip["category"])),
            str(chip["label"]),
            chip.get("source_refs", []),
            chip.get("evidence_refs", []),
            min(0.92, 0.35 + float(chip["confidence"])),
            float(chip["confidence"]),
        )

    for row in source_rows[:8]:
        clauses = [clause for clause in extract_clauses(row["raw_text"]) if len(clause.strip()) > 28 and not is_technical_residue(clause)]
        for index, clause in enumerate(clauses[:6]):
            add_segment(
                f"source:{row['source_ref']}:{index + 1}",
                "source_clause",
                row.get("display_label") or row["source_ref"],
                normalize_fact_label(clause) or clause,
                [row["source_ref"]],
                [],
                0.34,
                0.44,
            )

    return sorted(segments, key=lambda segment: (segment["importance"], segment["confidence"]), reverse=True)[:40]


def humanize_fact_category(value: str) -> str:
    if value == "pricing":
        return "Pricing"
    if value == "offer":
        return "Offer"
    if value == "positioning":
        return "Positioning"
    if value == "proof":
        return "Proof"
    if value == "segment":
        return "Segment"
    if value == "timing":
        return "Timing"
    if value == "opportunity":
        return "Opportunity"
    if value == "competitor":
        return "Competitor"
    return value.replace("_", " ").title()


def write_tasks_from_segments(
    source: SourcePackage,
    observations: list[dict[str, Any]],
    draft_segments: list[dict[str, Any]],
    knowledge_cards: list[dict[str, Any]],
    fact_chips: list[dict[str, Any]],
    evidence_units: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]] | None = None,
    generation_memory_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for segment in draft_segments:
        task = segment_to_task(source, segment, observations, knowledge_cards, fact_chips, evidence_units)
        if task:
            candidates.append(task)

    has_actionable_candidates = any(
        task.get("task_type") in {"direct_competitive_move", "tactical_response", "capture_move", "competitive_response", "general_business_value"}
        for task in candidates
    )
    if len(candidates) < 3:
        candidates.extend(build_missing_information_tasks(source, draft_segments, fact_chips, has_actionable_candidates))

    judged = judge_tasks(candidates[:12], source, feedback_rows or [], generation_memory_rows or [])
    if not judged:
        return {
            "reason": "We could not derive three distinct, high-confidence actions from the supplied evidence.",
        }
    return {
        "recommended_tasks": judged[:3],
        "summary": "We wrote three judged actions from the drafted knowledge segments and available evidence.",
    }


def _clip_task_copy(value: str | None, max_len: int = 320) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _organic_task_focus(
    *,
    strongest_excerpt: str,
    explicit_claim: str | None = None,
    offer: str | None = None,
    explicit_asset: str | None = None,
    explicit_section: str | None = None,
    max_len: int = 240,
) -> str:
    parts: list[str] = []
    for p in (explicit_claim, offer, explicit_asset, explicit_section):
        c = _clip_task_copy(str(p), max_len) if p and str(p).strip() else ""
        if c:
            parts.append(c)
    base = _clip_task_copy(strongest_excerpt, max_len)
    if base:
        parts.append(base)
    seen: set[str] = set()
    deduped: list[str] = []
    for p in parts:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        deduped.append(p)
    merged = " · ".join(deduped) if deduped else base
    return _clip_task_copy(merged, max_len + 120)


def segment_to_task(
    source: SourcePackage,
    segment: dict[str, Any],
    observations: list[dict[str, Any]],
    knowledge_cards: list[dict[str, Any]],
    fact_chips: list[dict[str, Any]],
    evidence_units: list[dict[str, Any]],
) -> dict[str, Any] | None:
    segment_text = str(segment["segment_text"])
    lowered = segment_text.lower()
    evidence_refs = segment.get("evidence_refs") or [f"segment::{segment['segment_id']}"]
    domain = infer_domain_from_sources(source, fact_chips)
    detail = extract_action_detail(segment_text)
    competitor = infer_segment_competitor(segment_text, source)
    if str(segment.get("segment_id") or "").startswith("intel_card::"):
        preferred = _intel_segment_preferred_competitor(segment_text, observations)
        if preferred:
            competitor = preferred
    audience = infer_operator_audience(domain, detail, segment_lowered=lowered)
    primary_channel = infer_primary_channel(domain, lowered)
    comparison_channel = "pricing page" if "pricing" in lowered or "onboarding" in lowered else primary_channel
    timing_window = detail.get("timeframe") or "this week"
    move_bucket = infer_task_move_bucket(segment["segment_kind"], lowered)
    supporting_source_bundle, strongest_excerpt = select_task_support_bundle(
        segment_text=segment_text,
        segment_source_refs=list(segment.get("source_refs") or []),
        evidence_units=evidence_units,
        competitor=competitor,
        move_bucket=move_bucket,
    )
    supporting_source_refs = [item["source_ref"] for item in supporting_source_bundle]
    if not strongest_excerpt:
        strongest_excerpt = segment_text
    supporting_signal_bundle = select_task_support_signals(
        segment_text=segment_text,
        observations=observations,
        supporting_source_refs=supporting_source_refs,
        competitor=competitor,
        move_bucket=move_bucket,
    )
    supporting_signal_refs = [item["signal_id"] for item in supporting_signal_bundle]
    supporting_segment_bundle = select_task_support_segments(
        segment=segment,
        move_bucket=move_bucket,
        competitor=competitor,
    )
    supporting_segment_ids = [item["segment_id"] for item in supporting_segment_bundle]
    strongest_unit = strongest_supporting_unit(
        supporting_source_refs=supporting_source_refs,
        evidence_units=evidence_units,
        strongest_excerpt=strongest_excerpt,
        move_bucket=move_bucket,
        segment_text=segment_text,
        competitor=competitor,
    )
    explicit_asset = str((strongest_unit or {}).get("asset") or detail.get("asset") or "").strip() or None
    explicit_section = str((strongest_unit or {}).get("section") or detail.get("section") or "").strip() or None
    explicit_claim = str((strongest_unit or {}).get("claim") or detail.get("claim") or "").strip() or None
    explicit_channel = str((strongest_unit or {}).get("channel") or detail.get("channel") or "").strip() or None
    bundle_observations = [
        observation
        for observation in observations
        if observation.get("signal_id") in supporting_signal_refs
    ]
    has_proof_signal = _word_boundary_any(lowered, ("proof", "testimonial", "integration", "trust"))
    has_offer_signal = _commercial_offer_tokens_in_text(lowered)

    if segment["segment_kind"] in {"pricing", "pricing_packaging"} or _commercial_pricing_tokens_in_text(lowered):
        competitor_name = competitor or fallback_competitor_reference(
            strongest_excerpt=strongest_excerpt,
            explicit_claim=explicit_claim,
        )
        comparison_channel = explicit_channel or comparison_channel
        mechanism = _clip_task_copy(strongest_excerpt, 420) or "pricing_or_offer_move"
        title = synthesize_task_title(
            move_bucket="pricing_or_offer_move",
            competitor=competitor_name,
            audience=audience,
            channel=comparison_channel,
            timing_window=timing_window,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        why_now = synthesize_task_why_now(
            move_bucket="pricing_or_offer_move",
            strongest_excerpt=strongest_excerpt,
            observations=bundle_observations,
            competitor=competitor_name,
            audience=audience,
            channel=comparison_channel,
            explicit_claim=explicit_claim,
        )
        expected_advantage = synthesize_task_expected_advantage(
            move_bucket="pricing_or_offer_move",
            competitor=competitor_name,
            audience=audience,
            channel=comparison_channel,
            timing_window=timing_window,
            explicit_claim=explicit_claim,
        )
        execution_steps = build_task_execution_steps(
            move_bucket="pricing_or_offer_move",
            source_refs=supporting_source_refs,
            channel=comparison_channel,
            audience=audience,
            competitor=competitor_name,
            mechanism=mechanism,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        return {
            "rank": 0,
            "title": title,
            "why_now": why_now,
            "expected_advantage": expected_advantage,
            "evidence_refs": evidence_refs,
            "task_type": "direct_competitive_move",
            "move_bucket": "pricing_or_offer_move",
            "competitor_name": competitor_name,
            "target_channel": comparison_channel,
            "target_segment": audience,
            "mechanism": mechanism,
            "done_definition": synthesize_done_definition(
                move_bucket="pricing_or_offer_move",
                competitor=competitor_name,
                channel=comparison_channel,
                audience=audience,
                mechanism=mechanism,
                strongest_excerpt=strongest_excerpt,
                explicit_asset=explicit_asset,
                explicit_section=explicit_section,
            ),
            "execution_steps": execution_steps,
            "supporting_signal_refs": supporting_signal_refs,
            "supporting_segment_ids": supporting_segment_ids,
            "supporting_signal_scores": supporting_signal_bundle,
            "supporting_segment_scores": supporting_segment_bundle,
            "supporting_source_refs": supporting_source_refs,
            "supporting_source_scores": supporting_source_bundle,
            "strongest_evidence_excerpt": strongest_excerpt,
        }
    if segment["segment_kind"] in {"proof"} or (has_proof_signal and not has_offer_signal):
        competitor_name = competitor or fallback_competitor_reference(
            strongest_excerpt=strongest_excerpt,
            explicit_claim=explicit_claim,
        )
        proof_channel = explicit_channel or infer_proof_channel(domain, lowered)
        mechanism = _clip_task_copy(strongest_excerpt, 420) or "proof_or_trust_move"
        title = synthesize_task_title(
            move_bucket="proof_or_trust_move",
            competitor=competitor_name,
            audience=audience,
            channel=proof_channel,
            timing_window=timing_window,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        why_now = synthesize_task_why_now(
            move_bucket="proof_or_trust_move",
            strongest_excerpt=strongest_excerpt,
            observations=bundle_observations,
            competitor=competitor_name,
            audience=audience,
            channel=proof_channel,
            explicit_claim=explicit_claim,
        )
        expected_advantage = synthesize_task_expected_advantage(
            move_bucket="proof_or_trust_move",
            competitor=competitor_name,
            audience=audience,
            channel=proof_channel,
            timing_window=timing_window,
            explicit_claim=explicit_claim,
        )
        execution_steps = build_task_execution_steps(
            move_bucket="proof_or_trust_move",
            source_refs=supporting_source_refs,
            channel=proof_channel,
            audience=audience,
            competitor=competitor_name,
            mechanism=mechanism,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        return {
            "rank": 0,
            "title": title,
            "why_now": why_now,
            "expected_advantage": expected_advantage,
            "evidence_refs": evidence_refs,
            "task_type": "general_business_value",
            "move_bucket": "proof_or_trust_move",
            "competitor_name": competitor_name,
            "target_channel": proof_channel,
            "target_segment": audience,
            "mechanism": mechanism,
            "done_definition": synthesize_done_definition(
                move_bucket="proof_or_trust_move",
                competitor=competitor_name,
                channel=proof_channel,
                audience=audience,
                mechanism=mechanism,
                strongest_excerpt=strongest_excerpt,
                explicit_asset=explicit_asset,
                explicit_section=explicit_section,
            ),
            "execution_steps": execution_steps,
            "supporting_signal_refs": supporting_signal_refs,
            "supporting_segment_ids": supporting_segment_ids,
            "supporting_signal_scores": supporting_signal_bundle,
            "supporting_segment_scores": supporting_segment_bundle,
            "supporting_source_refs": supporting_source_refs,
            "supporting_source_scores": supporting_source_bundle,
            "strongest_evidence_excerpt": strongest_excerpt,
        }
    if (
        segment["segment_kind"] in {"offer", "offer_positioning", "positioning"}
        or has_offer_signal
        or _word_boundary_any(lowered, ("homepage", "hero", "comparison"))
    ):
        competitor_name = competitor or fallback_competitor_reference(
            strongest_excerpt=strongest_excerpt,
            explicit_claim=explicit_claim,
        )
        offer = detail.get("offer") or strongest_offer_hint(segment_text)
        channel = explicit_channel or primary_channel
        mechanism = _clip_task_copy(strongest_excerpt, 420) or "messaging_or_positioning_move"
        title = synthesize_task_title(
            move_bucket="messaging_or_positioning_move",
            competitor=competitor_name,
            audience=audience,
            channel=channel,
            timing_window=timing_window,
            strongest_excerpt=strongest_excerpt,
            offer=offer,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        why_now = synthesize_task_why_now(
            move_bucket="messaging_or_positioning_move",
            strongest_excerpt=strongest_excerpt,
            observations=bundle_observations,
            competitor=competitor_name,
            audience=audience,
            channel=channel,
            explicit_claim=explicit_claim,
        )
        expected_advantage = synthesize_task_expected_advantage(
            move_bucket="messaging_or_positioning_move",
            competitor=competitor_name,
            audience=audience,
            channel=channel,
            timing_window=timing_window,
            explicit_claim=explicit_claim,
        )
        execution_steps = build_task_execution_steps(
            move_bucket="messaging_or_positioning_move",
            source_refs=supporting_source_refs,
            channel=channel,
            audience=audience,
            competitor=competitor_name,
            mechanism=mechanism,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        return {
            "rank": 0,
            "title": title,
            "why_now": why_now,
            "expected_advantage": expected_advantage,
            "evidence_refs": evidence_refs,
            "task_type": "tactical_response",
            "move_bucket": "messaging_or_positioning_move",
            "competitor_name": competitor_name,
            "target_channel": channel,
            "target_segment": audience,
            "mechanism": mechanism,
            "done_definition": synthesize_done_definition(
                move_bucket="messaging_or_positioning_move",
                competitor=competitor_name,
                channel=channel,
                audience=audience,
                mechanism=mechanism,
                strongest_excerpt=strongest_excerpt,
                explicit_asset=explicit_asset,
                explicit_section=explicit_section,
            ),
            "execution_steps": execution_steps,
            "supporting_signal_refs": supporting_signal_refs,
            "supporting_segment_ids": supporting_segment_ids,
            "supporting_signal_scores": supporting_signal_bundle,
            "supporting_segment_scores": supporting_segment_bundle,
            "supporting_source_refs": supporting_source_refs,
            "supporting_source_scores": supporting_source_bundle,
            "strongest_evidence_excerpt": strongest_excerpt,
        }
    if segment["segment_kind"] in {"open_questions", "timing"} or any(token in lowered for token in ("region", "unknown", "need", "add one source", "gap", "confirm")):
        title = synthesize_task_title(
            move_bucket="information_request",
            competitor=competitor or fallback_competitor_reference(
                strongest_excerpt=strongest_excerpt,
                explicit_claim=explicit_claim,
            ),
            audience=audience,
            channel="same workspace",
            timing_window=timing_window,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        comp_for_copy = competitor or fallback_competitor_reference(
            strongest_excerpt=strongest_excerpt,
            explicit_claim=explicit_claim,
        )
        why_now = synthesize_task_why_now(
            move_bucket="information_request",
            strongest_excerpt=strongest_excerpt,
            observations=bundle_observations,
            competitor=comp_for_copy,
            audience=audience,
            channel="same workspace",
            explicit_claim=explicit_claim,
        )
        info_mech = _clip_task_copy(strongest_excerpt, 420) or "information_request"
        expected_advantage = synthesize_task_expected_advantage(
            move_bucket="information_request",
            competitor=comp_for_copy,
            audience=audience,
            channel="same workspace",
            timing_window=timing_window,
            explicit_claim=explicit_claim,
        )
        return {
            "rank": 0,
            "title": title,
            "why_now": why_now,
            "expected_advantage": expected_advantage,
            "evidence_refs": evidence_refs,
            "task_type": "information_request",
            "move_bucket": "information_request",
            "target_segment": audience,
            "execution_steps": build_task_execution_steps(
                move_bucket="information_request",
                source_refs=supporting_source_refs,
                channel="same workspace",
                audience=audience,
                competitor=comp_for_copy,
                mechanism=info_mech,
                strongest_excerpt=strongest_excerpt,
                explicit_asset=explicit_asset,
                explicit_section=explicit_section,
                explicit_claim=explicit_claim,
            ),
            "done_definition": synthesize_done_definition(
                move_bucket="information_request",
                competitor=comp_for_copy,
                channel="same workspace",
                audience=audience,
                mechanism=info_mech,
                strongest_excerpt=strongest_excerpt,
                explicit_asset=explicit_asset,
                explicit_section=explicit_section,
            ),
            "supporting_signal_refs": supporting_signal_refs,
            "supporting_segment_ids": supporting_segment_ids,
            "supporting_signal_scores": supporting_signal_bundle,
            "supporting_segment_scores": supporting_segment_bundle,
            "supporting_source_refs": supporting_source_refs,
            "supporting_source_scores": supporting_source_bundle,
            "strongest_evidence_excerpt": strongest_excerpt,
        }
    if segment["segment_kind"] in {"opportunity", "closure", "asset_sale"} or any(token in lowered for token in ("closure", "sell-off", "asset", "opportunity", "distress")):
        competitor_name = competitor or fallback_competitor_reference(
            strongest_excerpt=strongest_excerpt,
            explicit_claim=explicit_claim,
        )
        outreach_channel = explicit_channel or "direct outreach"
        mechanism = _clip_task_copy(strongest_excerpt, 420) or "intercept_or_capture_move"
        title = synthesize_task_title(
            move_bucket="intercept_or_capture_move",
            competitor=competitor_name,
            audience=audience,
            channel=outreach_channel,
            timing_window=timing_window,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        why_now = synthesize_task_why_now(
            move_bucket="intercept_or_capture_move",
            strongest_excerpt=strongest_excerpt,
            observations=bundle_observations,
            competitor=competitor_name,
            audience=audience,
            channel=outreach_channel,
            explicit_claim=explicit_claim,
        )
        expected_advantage = synthesize_task_expected_advantage(
            move_bucket="intercept_or_capture_move",
            competitor=competitor_name,
            audience=audience,
            channel=outreach_channel,
            timing_window=timing_window,
            explicit_claim=explicit_claim,
        )
        execution_steps = build_task_execution_steps(
            move_bucket="intercept_or_capture_move",
            source_refs=supporting_source_refs,
            channel=outreach_channel,
            audience=audience,
            competitor=competitor_name,
            mechanism=mechanism,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        return {
            "rank": 0,
            "title": title,
            "why_now": why_now,
            "expected_advantage": expected_advantage,
            "evidence_refs": evidence_refs,
            "task_type": "capture_move",
            "move_bucket": "intercept_or_capture_move",
            "competitor_name": competitor_name,
            "target_channel": outreach_channel,
            "target_segment": audience,
            "mechanism": mechanism,
            "done_definition": synthesize_done_definition(
                move_bucket="intercept_or_capture_move",
                competitor=competitor_name,
                channel=outreach_channel,
                audience=audience,
                mechanism=mechanism,
                strongest_excerpt=strongest_excerpt,
                explicit_asset=explicit_asset,
                explicit_section=explicit_section,
            ),
            "execution_steps": execution_steps,
            "supporting_signal_refs": supporting_signal_refs,
            "supporting_segment_ids": supporting_segment_ids,
            "supporting_signal_scores": supporting_signal_bundle,
            "supporting_segment_scores": supporting_segment_bundle,
            "supporting_source_refs": supporting_source_refs,
            "supporting_source_scores": supporting_source_bundle,
            "strongest_evidence_excerpt": strongest_excerpt,
        }
    if segment["importance"] >= 0.7:
        competitor_name = competitor or fallback_competitor_reference(
            strongest_excerpt=strongest_excerpt,
            explicit_claim=explicit_claim,
        )
        proof_channel = explicit_channel or infer_proof_channel(domain, lowered)
        mechanism = _clip_task_copy(strongest_excerpt, 420) or "proof_or_trust_move"
        title = synthesize_task_title(
            move_bucket="proof_or_trust_move",
            competitor=competitor_name,
            audience=audience,
            channel=proof_channel,
            timing_window=timing_window,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        why_now = synthesize_task_why_now(
            move_bucket="proof_or_trust_move",
            strongest_excerpt=strongest_excerpt,
            observations=bundle_observations,
            competitor=competitor_name,
            audience=audience,
            channel=proof_channel,
            explicit_claim=explicit_claim,
        )
        expected_advantage = synthesize_task_expected_advantage(
            move_bucket="proof_or_trust_move",
            competitor=competitor_name,
            audience=audience,
            channel=proof_channel,
            timing_window=timing_window,
            explicit_claim=explicit_claim,
        )
        execution_steps = build_task_execution_steps(
            move_bucket="proof_or_trust_move",
            source_refs=supporting_source_refs,
            channel=proof_channel,
            audience=audience,
            competitor=competitor_name,
            mechanism=mechanism,
            strongest_excerpt=strongest_excerpt,
            explicit_asset=explicit_asset,
            explicit_section=explicit_section,
            explicit_claim=explicit_claim,
        )
        return {
            "rank": 0,
            "title": title,
            "why_now": why_now,
            "expected_advantage": expected_advantage,
            "evidence_refs": evidence_refs,
            "task_type": "general_business_value",
            "move_bucket": "proof_or_trust_move" if any(token in lowered for token in ("proof", "testimonial", "integration", "trust")) else "messaging_or_positioning_move",
            "competitor_name": competitor_name,
            "target_channel": proof_channel,
            "target_segment": audience,
            "mechanism": mechanism,
            "done_definition": synthesize_done_definition(
                move_bucket="proof_or_trust_move",
                competitor=competitor_name,
                channel=proof_channel,
                audience=audience,
                mechanism=mechanism,
                strongest_excerpt=strongest_excerpt,
                explicit_asset=explicit_asset,
                explicit_section=explicit_section,
            ),
            "execution_steps": execution_steps,
            "supporting_signal_refs": supporting_signal_refs,
            "supporting_segment_ids": supporting_segment_ids,
            "supporting_signal_scores": supporting_signal_bundle,
            "supporting_segment_scores": supporting_segment_bundle,
            "supporting_source_refs": supporting_source_refs,
            "supporting_source_scores": supporting_source_bundle,
            "strongest_evidence_excerpt": strongest_excerpt,
        }
    return None


def build_missing_information_tasks(
    source: SourcePackage,
    draft_segments: list[dict[str, Any]],
    fact_chips: list[dict[str, Any]],
    has_actionable_candidates: bool,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    strongest = draft_segments[:3]
    domain = infer_domain_from_sources(source, fact_chips)
    strongest_competitor = normalize_competitor_fact(source.competitor or "") or fallback_competitor_reference(
        strongest_excerpt=source.raw_text,
        explicit_claim=None,
    )

    def append_from_segment(
        *,
        segment: dict[str, Any],
        move_bucket: str,
        task_type: str,
        channel: str,
    ) -> None:
        st = str(segment["segment_text"])
        lowered_segment = st.lower()
        detail = extract_action_detail(st)
        audience = infer_operator_audience(domain, detail, segment_lowered=lowered_segment)
        audience_phrase = normalize_task_audience(audience)
        evidence_refs = segment.get("evidence_refs") or [f"segment::{segment['segment_id']}"]
        candidates.append(
            {
                "rank": 0,
                "title": synthesize_task_title(
                    move_bucket=move_bucket,
                    competitor=strongest_competitor,
                    audience=audience_phrase,
                    channel=channel,
                    timing_window="this week",
                    strongest_excerpt=st,
                ),
                "why_now": synthesize_task_why_now(
                    move_bucket=move_bucket,
                    strongest_excerpt=st,
                    observations=[],
                    competitor=strongest_competitor,
                    audience=audience_phrase,
                    channel=channel,
                ),
                "expected_advantage": synthesize_task_expected_advantage(
                    move_bucket=move_bucket,
                    competitor=strongest_competitor,
                    audience=audience_phrase,
                    channel=channel,
                    timing_window="this week",
                ),
                "evidence_refs": evidence_refs,
                "task_type": task_type,
                "move_bucket": move_bucket,
            }
        )

    for segment in strongest:
        lowered_segment = str(segment["segment_text"]).lower()
        if segment["segment_kind"] == "competitor":
            append_from_segment(
                segment=segment,
                move_bucket="information_request",
                task_type="information_request",
                channel="same workspace",
            )
        elif segment["segment_kind"] == "proof" or _word_boundary_any(
            lowered_segment, ("proof", "testimonial", "integration", "trust")
        ):
            append_from_segment(
                segment=segment,
                move_bucket="proof_or_trust_move",
                task_type="general_business_value",
                channel=infer_proof_channel(domain, lowered_segment),
            )
        elif segment["segment_kind"] in {"pricing", "pricing_packaging"} or _commercial_pricing_tokens_in_text(
            lowered_segment
        ):
            append_from_segment(
                segment=segment,
                move_bucket="pricing_or_offer_move",
                task_type="direct_competitive_move",
                channel=infer_primary_channel(domain, lowered_segment),
            )
        elif segment["segment_kind"] in {"offer", "offer_positioning", "positioning"} or (
            _commercial_offer_tokens_in_text(lowered_segment)
            or _word_boundary_any(lowered_segment, ("positioning", "message", "homepage", "hero", "comparison"))
        ):
            append_from_segment(
                segment=segment,
                move_bucket="messaging_or_positioning_move",
                task_type="tactical_response",
                channel=infer_primary_channel(domain, lowered_segment),
            )
        elif segment["segment_kind"] == "source_clause":
            append_from_segment(
                segment=segment,
                move_bucket="messaging_or_positioning_move",
                task_type="general_business_value",
                channel=infer_primary_channel(domain, lowered_segment),
            )

    info_request_count = sum(1 for candidate in candidates if candidate.get("task_type") == "information_request")

    def append_workspace_request(*, excerpt: str, evidence_refs: list[str]) -> None:
        detail = extract_action_detail(excerpt)
        audience = infer_operator_audience(domain, detail, segment_lowered=excerpt.lower())
        audience_phrase = normalize_task_audience(audience)
        candidates.append(
            {
                "rank": 0,
                "title": synthesize_task_title(
                    move_bucket="information_request",
                    competitor=strongest_competitor,
                    audience=audience_phrase,
                    channel="same workspace",
                    timing_window="this week",
                    strongest_excerpt=excerpt,
                ),
                "why_now": synthesize_task_why_now(
                    move_bucket="information_request",
                    strongest_excerpt=excerpt,
                    observations=[],
                    competitor=strongest_competitor,
                    audience=audience_phrase,
                    channel="same workspace",
                ),
                "expected_advantage": synthesize_task_expected_advantage(
                    move_bucket="information_request",
                    competitor=strongest_competitor,
                    audience=audience_phrase,
                    channel="same workspace",
                    timing_window="this week",
                ),
                "evidence_refs": evidence_refs,
                "task_type": "information_request",
                "move_bucket": "information_request",
            }
        )

    if not candidates:
        ex = _clip_task_copy(
            " ".join(str(s.get("segment_text") or "") for s in strongest) or source.raw_text or source.source_ref,
            400,
        )
        append_workspace_request(
            excerpt=ex or source.source_ref,
            evidence_refs=[f"segment::{segment['segment_id']}" for segment in strongest[:2]] or [source.source_ref],
        )
    elif not has_actionable_candidates and info_request_count == 0:
        ex = _clip_task_copy(
            " ".join(str(s.get("segment_text") or "") for s in strongest) or source.raw_text,
            400,
        )
        append_workspace_request(
            excerpt=ex or source.raw_text or source.source_ref,
            evidence_refs=[f"segment::{segment['segment_id']}" for segment in strongest[:2]] or [source.source_ref],
        )

    if has_actionable_candidates and len(candidates) < 3:
        anchor_segment = strongest[0] if strongest else None
        anchor_raw = (anchor_segment.get("segment_text") if anchor_segment else None) or source.raw_text or ""
        anchor_text = str(anchor_raw).lower()
        channel = infer_primary_channel(domain, anchor_text)
        fallback_actions = [
            (
                "proof_or_trust_move",
                "exploratory_action",
                infer_proof_channel(domain, anchor_text),
            ),
            ("messaging_or_positioning_move", "exploratory_action", channel),
        ]
        existing_buckets = {str(candidate.get("move_bucket") or "") for candidate in candidates}
        for move_bucket, task_type, ch in fallback_actions:
            if len(candidates) >= 3:
                break
            if move_bucket in existing_buckets:
                continue
            synthetic = {
                "segment_id": anchor_segment["segment_id"] if anchor_segment else "synthetic::fallback",
                "segment_text": str(anchor_raw) or source.source_ref,
                "segment_kind": "open_questions",
            }
            append_from_segment(segment=synthetic, move_bucket=move_bucket, task_type=task_type, channel=ch)
            existing_buckets.add(move_bucket)

    return candidates


def judge_tasks(
    tasks: list[dict[str, Any]],
    source: SourcePackage,
    feedback_rows: list[dict[str, Any]],
    generation_memory_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    declined_keys = {
        normalize_task_key(str(row["original_title"]))
        for row in feedback_rows
        if row.get("feedback_type") in {"declined", "commented", "deleted_silent", "deleted_with_annotation", "held_for_later"}
    }
    seen: set[str] = set()
    judged: list[dict[str, Any]] = []
    for task in tasks:
        key = normalize_task_key(task["title"])
        if key in seen:
            continue
        if key in declined_keys:
            continue
        seen.add(key)
        judged.append(task)

    for row in feedback_rows:
        adjusted_text = str(row.get("adjusted_text") or "").strip()
        if row.get("feedback_type") != "edited" or not adjusted_text:
            continue
        key = normalize_task_key(adjusted_text)
        if key in seen:
            continue
        seen.add(key)
        prior = _clip_task_copy(str(row.get("original_title") or ""), 200)
        judged.insert(
            0,
            {
                "rank": 0,
                "title": adjusted_text,
                "why_now": (
                    f"Operator signal: feedback_id={row.get('feedback_id')} · prior_title={prior} · "
                    f"correction uses your edited wording as the source of truth."
                ),
                "expected_advantage": str(row.get("original_expected_advantage"))
                or synthesize_task_expected_advantage(
                    move_bucket="operator_corrected",
                    competitor=fallback_competitor_reference(strongest_excerpt=adjusted_text, explicit_claim=None),
                    audience="buyers",
                    channel="same workspace",
                    timing_window="this week",
                ),
                "evidence_refs": [f"feedback::{row['feedback_id']}"],
                "task_type": "operator_corrected",
                "move_bucket": "operator_corrected",
            },
        )

    info_request_limit = 1 if any(
        task.get("task_type") in {"direct_competitive_move", "tactical_response", "capture_move", "competitive_response", "general_business_value"}
        for task in judged
    ) else 3
    filtered: list[dict[str, Any]] = []
    info_request_seen = 0
    sorted_tasks = sorted(judged, key=lambda task: task_priority_score(task, generation_memory_rows), reverse=True)
    for task in sorted_tasks:
        if task.get("task_type") == "information_request":
            if info_request_seen >= info_request_limit:
                continue
            info_request_seen += 1
        filtered.append(task)

    final_tasks = select_diverse_tasks(
        sorted(filtered, key=lambda task: task_priority_score(task, generation_memory_rows), reverse=True),
        target_count=3,
    )
    non_info_final_count = sum(1 for task in final_tasks if task.get("task_type") != "information_request")
    if final_tasks and len(final_tasks) >= 3 and final_tasks[-1].get("task_type") == "information_request" and non_info_final_count >= 2:
        replacement = next(
            (
                task
                for task in sorted(filtered, key=lambda task: task_priority_score(task, generation_memory_rows), reverse=True)
                if task not in final_tasks and task.get("task_type") != "information_request"
            ),
            None,
        )
        if replacement:
            final_tasks[-1] = replacement
    if len(final_tasks) < 3:
        fallback_titles = {
            normalize_task_key(task["title"])
            for task in final_tasks
        }
        fallback_competitor = normalize_competitor_fact(source.competitor or "") or fallback_competitor_reference(
            strongest_excerpt=source.raw_text,
            explicit_claim=None,
        )
        domain_fb = infer_domain_from_sources(source, [])
        raw_fb = _clip_task_copy(source.raw_text, 360) or source.source_ref
        lowered_fb = raw_fb.lower()
        for index in range(len(final_tasks), 3):
            move_bucket = "proof_or_trust_move" if index == 2 else "messaging_or_positioning_move"
            channel_fb = (
                infer_proof_channel(domain_fb, lowered_fb)
                if move_bucket == "proof_or_trust_move"
                else infer_primary_channel(domain_fb, lowered_fb)
            )
            fallback_title = synthesize_task_title(
                move_bucket=move_bucket,
                competitor=fallback_competitor,
                audience="buyers",
                channel=channel_fb,
                timing_window="this week",
                strongest_excerpt=raw_fb,
            )
            normalized_title = normalize_task_key(fallback_title)
            if normalized_title in fallback_titles:
                move_bucket = "pricing_or_offer_move"
                channel_fb = infer_primary_channel(domain_fb, lowered_fb)
                fallback_title = synthesize_task_title(
                    move_bucket=move_bucket,
                    competitor=fallback_competitor,
                    audience="buyers",
                    channel=channel_fb,
                    timing_window="this week",
                    strongest_excerpt=raw_fb,
                )
                normalized_title = normalize_task_key(fallback_title)
            fallback_titles.add(normalized_title)
            final_tasks.append(
                {
                    "rank": 0,
                    "title": fallback_title,
                    "why_now": synthesize_task_why_now(
                        move_bucket=move_bucket,
                        strongest_excerpt=raw_fb,
                        observations=[],
                        competitor=fallback_competitor,
                        audience="buyers",
                        channel=channel_fb,
                    ),
                    "expected_advantage": synthesize_task_expected_advantage(
                        move_bucket=move_bucket,
                        competitor=fallback_competitor,
                        audience="buyers",
                        channel=channel_fb,
                        timing_window="this week",
                    ),
                    "evidence_refs": [source.source_ref],
                    "task_type": "exploratory_action",
                    "move_bucket": move_bucket,
                    "target_segment": "buyers",
                    "supporting_source_refs": [source.source_ref],
                    "strongest_evidence_excerpt": source.raw_text[:220] if source.raw_text else source.source_ref,
                }
            )

    now = datetime.now(UTC)
    for index, task in enumerate(final_tasks[:3], start=1):
        task["rank"] = index
        task["is_next_best_action"] = index == 1
        task["priority_label"] = "critical" if index == 1 else "high" if index == 2 else "normal"
        task["confidence_class"] = (
            "exploratory_action"
            if task.get("task_type") == "exploratory_action"
            else "strong_action"
            if index == 1
            else "moderate_action"
        )
        best_before_days = 2 if index == 1 else 4 if index == 2 else 6
        task["best_before"] = (now + timedelta(days=best_before_days)).date().isoformat()
    return final_tasks[:3]


def generate_guaranteed_task_triplet(
    source: SourcePackage,
    observations: list[dict[str, Any]],
    draft_segments: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
    generation_memory_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    strongest = draft_segments[:3]
    fallback_tasks: list[dict[str, Any]] = []
    domain = infer_domain_from_sources(source, [])
    strongest_competitor = normalize_competitor_fact(source.competitor or "") or fallback_competitor_reference(
        strongest_excerpt=source.raw_text,
        explicit_claim=None,
    )
    if strongest:
        for segment in strongest:
            st = str(segment["segment_text"])
            lowered = st.lower()
            detail = extract_action_detail(st)
            audience_phrase = normalize_task_audience(
                infer_operator_audience(domain, detail, segment_lowered=lowered)
            )
            cat = humanize_fact_category(str(segment["segment_kind"]).replace("open_questions", "market"))
            enriched = f"{st} · segment_kind={segment['segment_kind']} · category={cat}"
            fallback_tasks.append(
                {
                    "rank": 0,
                    "title": synthesize_task_title(
                        move_bucket="information_request",
                        competitor=strongest_competitor,
                        audience=audience_phrase,
                        channel="same workspace",
                        timing_window="this week",
                        strongest_excerpt=enriched,
                    ),
                    "why_now": synthesize_task_why_now(
                        move_bucket="information_request",
                        strongest_excerpt=enriched,
                        observations=[],
                        competitor=strongest_competitor,
                        audience=audience_phrase,
                        channel="same workspace",
                    ),
                    "expected_advantage": synthesize_task_expected_advantage(
                        move_bucket="information_request",
                        competitor=strongest_competitor,
                        audience=audience_phrase,
                        channel="same workspace",
                        timing_window="this week",
                    ),
                    "evidence_refs": segment.get("evidence_refs") or [f"segment::{segment['segment_id']}"],
                    "task_type": "exploratory_action",
                    "move_bucket": "information_request",
                }
            )
    while len(fallback_tasks) < 3:
        ex = _clip_task_copy(source.raw_text, 400) or source.source_ref
        detail = extract_action_detail(str(source.raw_text or ""))
        audience_phrase = normalize_task_audience(
            infer_operator_audience(
                domain, detail, segment_lowered=(source.raw_text or "").lower()
            )
        )
        fallback_tasks.append(
            {
                "rank": 0,
                "title": synthesize_task_title(
                    move_bucket="information_request",
                    competitor=strongest_competitor,
                    audience=audience_phrase,
                    channel="same workspace",
                    timing_window="this week",
                    strongest_excerpt=f"{ex} · fill_index={len(fallback_tasks)}",
                ),
                "why_now": synthesize_task_why_now(
                    move_bucket="information_request",
                    strongest_excerpt=ex,
                    observations=[],
                    competitor=strongest_competitor,
                    audience=audience_phrase,
                    channel="same workspace",
                ),
                "expected_advantage": synthesize_task_expected_advantage(
                    move_bucket="information_request",
                    competitor=strongest_competitor,
                    audience=audience_phrase,
                    channel="same workspace",
                    timing_window="this week",
                ),
                "evidence_refs": [source.source_ref],
                "task_type": "exploratory_action",
                "move_bucket": "information_request",
            }
        )
    judged = judge_tasks(fallback_tasks[:6], source, feedback_rows, generation_memory_rows)
    return {
        "recommended_tasks": judged[:3],
        "summary": "Three tasks were emitted from your workspace segments because the checklist cannot be empty.",
    }


def generate_learning_checklist(
    source_package: SourcePackage,
    observations: list[dict[str, Any]],
    draft_segments: list[dict[str, Any]],
    knowledge_cards: list[dict[str, Any]],
    fact_chips: list[dict[str, Any]],
    evidence_units: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
    generation_memory_rows: list[dict[str, Any]],
    retained_tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    segment_payload = write_tasks_from_segments(
        source_package,
        observations,
        draft_segments,
        knowledge_cards,
        fact_chips,
        evidence_units,
        feedback_rows,
        generation_memory_rows,
    )

    legacy_payload = generate_recommended_tasks(source_package, observations)
    repaired_legacy_payload: dict[str, Any] | None = None
    if "recommended_tasks" in legacy_payload:
        try:
            validate_result_payload(source_package.project_id, legacy_payload, run_id="precheck")
        except ValidationError:
            repaired_legacy_payload = repair_recommended_tasks(source_package, observations, legacy_payload)

    candidate_payloads: list[tuple[str, dict[str, Any]]] = []
    for label, payload in (
        ("segment", segment_payload),
        ("legacy_repaired", repaired_legacy_payload),
        ("legacy", legacy_payload),
    ):
        if not payload or "recommended_tasks" not in payload:
            continue
        try:
            validate_result_payload(source_package.project_id, payload, run_id=label)
            candidate_payloads.append((label, payload))
        except ValidationError:
            continue

    chosen_payload = None
    if candidate_payloads:
        candidate_payloads.sort(
            key=lambda item: (task_payload_specificity_score(item[1]), 1 if item[0] == "segment" else 0),
            reverse=True,
        )
        chosen_payload = candidate_payloads[0][1]
    else:
        chosen_payload = generate_guaranteed_task_triplet(
            source_package,
            observations,
            draft_segments,
            feedback_rows,
            generation_memory_rows,
        )

    retained_tasks = retained_tasks or []
    if not retained_tasks:
        return chosen_payload

    # Find the declined task's move bucket to prefer a different bucket for replacements
    declined_buckets: set[str] = set()
    for t in retained_tasks:
        # Retained tasks are those NOT declined; check what was removed by examining
        # whether the chosen_payload contains the same bucket already
        pass
    # Get buckets already in retained tasks — prefer those NOT present for replacements
    retained_task_buckets = {task_move_bucket(t) for t in retained_tasks}

    merged_tasks = []
    retained_titles: set[str] = set()
    for t in retained_tasks:
        merged_tasks.append(dict(t))
        retained_titles.add(normalize_task_key(t.get("title", "")))

    for t in chosen_payload.get("recommended_tasks", []):
        if len(merged_tasks) >= 3:
            break
        key = normalize_task_key(t.get("title", ""))
        candidate_bucket = task_move_bucket(t)

        # Semantic duplicate guard (Jaccard 60%)
        is_duplicate = False
        tw = set(key.split())
        for rt in retained_titles:
            rw = set(rt.split())
            if len(tw | rw) > 0 and len(tw & rw) / len(tw | rw) > 0.6:
                is_duplicate = True
                break
        if is_duplicate:
            continue

        # Post-generation quality gate:
        # 1. Skip tasks with synthetic doubled competitor name pattern
        title = str(t.get("title") or "")
        if re.search(r"(the competitor using .{5,60})\s+\1", title, re.IGNORECASE):
            t["quality_class"] = "rejected_phrasing"
            continue
        # 2. Cap title length at 20 words
        title_words = title.split()
        if len(title_words) > 20:
            t["title"] = " ".join(title_words[:20])

        # 3. Mark exploratory tasks explicitly — do NOT give them urgency framing
        is_exploratory = any(
            title.lower().startswith(prefix)
            for prefix in ("explore ", "request one", "gather ", "ask for", "find out", "research ")
        )
        if is_exploratory:
            t["quality_class"] = "exploratory"
            t["priority_label"] = "exploratory"
            # Force exploratory tasks to come after strong-action tasks
            if len(merged_tasks) < 2 and len(retained_task_buckets) > 0:
                # Skip for first 2 slots — prefer a different strong move
                continue

        # 4. Prefer a different move bucket than retained tasks for first replacement
        if candidate_bucket in retained_task_buckets and len(merged_tasks) < len(retained_tasks) + 1:
            # Deprioritize — put at end by not adding now, but allow below after loop
            declined_buckets.add(candidate_bucket)
            continue

        merged_tasks.append(dict(t))
        retained_titles.add(key)

    # Second pass: allow same-bucket tasks if we still need more tasks
    if len(merged_tasks) < 3:
        for t in chosen_payload.get("recommended_tasks", []):
            if len(merged_tasks) >= 3:
                break
            key = normalize_task_key(t.get("title", ""))
            if key in retained_titles:
                continue
            is_duplicate = False
            tw = set(key.split())
            for rt in retained_titles:
                rw = set(rt.split())
                if len(tw | rw) > 0 and len(tw & rw) / len(tw | rw) > 0.6:
                    is_duplicate = True
                    break
            if is_duplicate:
                continue
            merged_tasks.append(dict(t))
            retained_titles.add(key)

    if len(merged_tasks) < 3:
        fallback_triplet = generate_guaranteed_task_triplet(
            source_package, observations, draft_segments, feedback_rows, generation_memory_rows
        )
        for ft in fallback_triplet.get("recommended_tasks", []):
            if len(merged_tasks) >= 3:
                break
            key = normalize_task_key(ft.get("title", ""))
            if key not in retained_titles:
                merged_tasks.append(dict(ft))
                retained_titles.add(key)

    for i, t in enumerate(merged_tasks[:3]):
        t["rank"] = i + 1
        t["is_next_best_action"] = (i == 0)
        t["priority_label"] = "critical" if i == 0 else "high" if i == 1 else "normal"

    return {
        "recommended_tasks": merged_tasks[:3],
        "summary": "Merged retained tasks with generated replacements.",
    }


def validate_result_payload(project_id: str, payload: dict[str, Any], *, run_id: str) -> None:
    validate_job_result(
        {
            "job_id": run_id,
            "app_id": "worker",
            "project_id": project_id,
            "status": "complete",
            "completed_at": utc_now_iso(),
            "result_payload": payload,
        }
    )


def task_payload_specificity_score(payload: dict[str, Any]) -> int:
    tasks = payload.get("recommended_tasks") or []
    if not isinstance(tasks, list):
        return -100

    score = 0
    for task in tasks:
        title = str(task.get("title") or "").lower()
        why_now = str(task.get("why_now") or "").lower()
        expected_advantage = str(task.get("expected_advantage") or "").lower()
        done_definition = str(task.get("done_definition") or "").lower()
        strongest_excerpt = str(task.get("strongest_evidence_excerpt") or "").lower()

        if task.get("competitor_name"):
            score += 2
        if task.get("target_channel"):
            score += 2
        if task.get("target_segment"):
            score += 1
        if task.get("done_definition"):
            score += 2
        if task.get("execution_steps"):
            score += 2
        if strongest_excerpt:
            score += 2
        if any(token in title for token in ("pricing page", "homepage", "hero section", "proof block", "comparison block", "faq")):
            score += 3
        if any(token in title + " " + why_now + " " + expected_advantage for token in ("free trial", "no engineering required", "onboarding", "pricing comparison", "testimonial")):
            score += 3
        if any(token in title + " " + why_now + " " + expected_advantage + " " + done_definition for token in ("the worker drafted", "current competitor frame", "buyer-facing response", "use the linked intelligence")):
            score -= 6
        if any(token == str(task.get("competitor_name") or "").strip().lower() for token in ("add", "rewrite", "publish", "launch", "request", "check", "pull")):
            score -= 8
    return score


def task_priority_score(task: dict[str, Any], generation_memory_rows: list[dict[str, Any]] | None = None) -> int:
    title = str(task.get("title") or "").lower()
    why = str(task.get("why_now") or "").lower()
    score = 0
    task_type = task.get("task_type")
    if task_type == "capture_move":
        score += 6
    elif task_type == "direct_competitive_move":
        score += 5
    elif task_type in {"tactical_response", "competitive_response"}:
        score += 4
    elif task_type == "general_business_value":
        score += 3
    elif task_type == "information_request":
        score += 1
    if "this week" in title or "this week" in why:
        score += 3
    if any(token in title or token in why for token in ("before", "closure", "capture", "pricing")):
        score += 3
    if re.search(r"\btrial\b", title) or re.search(r"\btrial\b", why):
        score += 3
    # Title embeds move=pricing_or_offer_move (underscore breaks \boffer\b); avoid substring "offer" in "offered".
    if (
        "pricing_or_offer_move" in title
        or "pricing_or_offer_move" in why
        or re.search(r"\boffer\b", title)
        or re.search(r"\boffer\b", why)
    ):
        score += 3
    score += generation_memory_adjustment(task, generation_memory_rows or [])
    return score


def generation_memory_adjustment(task: dict[str, Any], generation_memory_rows: list[dict[str, Any]]) -> int:
    if not generation_memory_rows:
        return 0

    normalized_title = normalize_task_key(task.get("title", ""))
    bucket = task_move_bucket(task)
    title_lc = str(task.get("title") or "").lower()
    channel = infer_primary_channel("academy" if "enrollment" in title_lc else "general", title_lc)
    adjustment = 0
    for row in generation_memory_rows:
        kind = str(row.get("memory_kind") or "")
        pattern_key = str(row.get("pattern_key") or "")
        signal_value = str(row.get("signal_value") or "")
        weight = int(round(float(row.get("weight") or 0)))
        if kind == "avoid_title":
            if avoid_title_pattern_matches(normalized_title, pattern_key):
                adjustment -= max(5, weight * 2)
        elif kind == "avoid_phrase" and signal_value and signal_value in title_lc:
            adjustment -= max(3, weight)
        elif kind == "avoid_bucket" and pattern_key == bucket:
            adjustment -= max(1, weight)
        elif kind == "prefer_channel" and signal_value and signal_value == channel:
            adjustment += max(2, weight)
        elif kind == "prefer_bucket" and pattern_key == bucket:
            adjustment += max(3, weight)
        elif kind == "prefer_phrase" and signal_value and signal_value in title_lc:
            adjustment += max(2, weight)
    return adjustment


def build_generation_memory_rows(feedback_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in feedback_rows:
        feedback_id = str(row.get("feedback_id") or "")
        feedback_type = str(row.get("feedback_type") or "")
        original_title = str(row.get("original_title") or "")
        normalized_title = normalize_task_key(original_title)
        adjusted_text = str(row.get("adjusted_text") or "").strip()
        comment = str(row.get("feedback_comment") or "").strip().lower()

        # Penalize the declined/deleted task title
        if feedback_type in {"declined", "commented", "deleted_with_annotation", "held_for_later"} and normalized_title:
            weight = 3.0 if feedback_type in {"declined", "deleted_with_annotation"} else 2.0 if feedback_type == "commented" else 1.0
            rows.append({
                "memory_kind": "avoid_title",
                "pattern_key": normalized_title,
                "signal_value": original_title,
                "weight": weight,
                "source_feedback_id": feedback_id,
            })

        # Parse structured signals from comment using the full comment parser
        if comment:
            rows.extend(extract_comment_signals(comment, feedback_id))

        # Positive signals from edited task text
        if adjusted_text:
            adjusted_lower = adjusted_text.lower()
            rows.append({
                "memory_kind": "prefer_phrase",
                "pattern_key": normalize_task_key(adjusted_text),
                "signal_value": adjusted_lower,
                "weight": 2.0,
                "source_feedback_id": feedback_id,
            })
            preferred_channel = infer_primary_channel(
                "academy" if "enrollment" in adjusted_lower else "general", adjusted_lower
            )
            rows.append({
                "memory_kind": "prefer_channel",
                "pattern_key": task_move_bucket({"title": adjusted_text, "why_now": "", "task_type": ""}),
                "signal_value": preferred_channel,
                "weight": 1.0,
                "source_feedback_id": feedback_id,
            })
    return rows

def task_move_bucket(task: dict[str, Any]) -> str:
    bucket = str(task.get("move_bucket") or "").strip()
    if bucket:
        return bucket

    task_type = str(task.get("task_type") or "")
    if task_type == "capture_move":
        return "intercept_or_capture_move"
    if task_type == "direct_competitive_move":
        return "pricing_or_offer_move"
    if task_type in {"tactical_response", "competitive_response"}:
        return "messaging_or_positioning_move"
    if task_type == "information_request":
        return "information_request"
    if task_type == "operator_corrected":
        return "operator_corrected"

    text = f"{task.get('title', '')} {task.get('why_now', '')}".lower()
    if _commercial_pricing_tokens_in_text(text) or _commercial_offer_tokens_in_text(text):
        return "pricing_or_offer_move"
    if any(token in text for token in ("capture", "asset", "closure", "staff", "distribution")):
        return "intercept_or_capture_move"
    if any(token in text for token in ("proof", "testimonial", "trust", "integration")):
        return "proof_or_trust_move"
    if any(token in text for token in ("partner", "referral", "channel", "distribution")):
        return "partnership_or_distribution_move"
    return "messaging_or_positioning_move"


def select_diverse_tasks(tasks: list[dict[str, Any]], target_count: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_buckets: set[str] = set()

    for task in tasks:
        bucket = task_move_bucket(task)
        if bucket in seen_buckets:
            continue
        selected.append(task)
        seen_buckets.add(bucket)
        if len(selected) >= target_count:
            return selected

    for task in tasks:
        if task in selected:
            continue
        selected.append(task)
        if len(selected) >= target_count:
            break
    return selected


def task_title_jaccard(title_a: str, title_b: str) -> float:
    """Token Jaccard on normalized titles; used for duplicate / replacement checks in tests and gates."""
    wa = set(normalize_task_key(title_a).split())
    wb = set(normalize_task_key(title_b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def normalize_legacy_product_voice(value: str) -> str:
    text = str(value or "")
    replacements = {
        "The current source set is building a market picture even if there is no immediate checklist move yet.": "We are building a market picture from your source set even if there is no immediate checklist move yet.",
        "Use this summary to decide whether the market is shifting toward pricing pressure, offer pressure, or proof-based positioning pressure.": "Use this summary to decide whether your market is shifting toward pricing pressure, offer pressure, or proof-based positioning pressure.",
        "The worker drafted a pricing segment from the source set:": "We drafted a pricing segment from your source set:",
        "The worker drafted a buyer-pressure segment:": "We drafted a buyer-pressure segment from your source set:",
        "The worker found a signal gap that blocks a stronger recommendation:": "We found a signal gap that blocks a stronger recommendation:",
        "The worker drafted an asymmetric opportunity segment:": "We drafted an asymmetric opportunity segment from your source set:",
        "The worker synthesized a high-importance competitor signal from the source set:": "We synthesized a high-importance competitor signal from your source set:",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def normalize_legacy_product_voice_in_segment(segment: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(segment)
    normalized["segment_text"] = normalize_legacy_product_voice(str(segment.get("segment_text") or ""))
    normalized["title"] = normalize_legacy_product_voice(str(segment.get("title") or ""))
    return normalized


def infer_segment_competitor(segment_text: str, source: SourcePackage) -> str | None:
    candidates: list[str] = []
    if source.competitor:
        candidates.append(source.competitor)
    candidates.extend(extract_named_entities(segment_text))
    for candidate in candidates:
        cleaned = clean_entity(candidate)
        if cleaned and not is_placeholder_entity(cleaned):
            return cleaned
    return None


def infer_operator_audience(
    domain: str, detail: dict[str, str | None], *, segment_lowered: str = ""
) -> str:
    """Audience label derived from domain plus wording in the user's segment (not a global default)."""
    sl = segment_lowered.lower()
    youth_markers = (
        "family",
        "families",
        "parent",
        "u10",
        "u11",
        "u12",
        "u13",
        "u14",
        "u15",
        "youth",
        "kids",
        "junior",
        "intake",
        "enrollment",
        "student athlete",
    )
    tier = detail.get("tier")
    if domain == "academy" and any(m in sl for m in youth_markers):
        return f"{tier} families" if tier else "families"
    if domain == "academy":
        return "buyers"
    return "buyers"


def infer_primary_channel(domain: str, lowered_text: str) -> str:
    if "homepage" in lowered_text or "hero" in lowered_text:
        return "homepage comparison section"
    if "pricing" in lowered_text:
        return "pricing page"
    if "enrollment" in lowered_text:
        return "enrollment path"
    if "sales" in lowered_text or "call" in lowered_text:
        return "sales script"
    return "enrollment path" if domain == "academy" else "homepage comparison section"


def infer_proof_channel(domain: str, lowered_text: str) -> str:
    if "pricing" in lowered_text:
        return "pricing page and comparison section"
    if "sales" in lowered_text:
        return "sales script and follow-up email"
    return "enrollment page and comparison section" if domain == "academy" else "homepage and comparison section"


def strongest_supporting_unit(
    *,
    supporting_source_refs: list[str],
    evidence_units: list[dict[str, Any]],
    strongest_excerpt: str,
    move_bucket: str,
    segment_text: str,
    competitor: str | None,
) -> dict[str, Any] | None:
    normalized_excerpt = strongest_excerpt.strip().lower()
    candidates = [
        unit
        for unit in evidence_units
        if unit.get("source_ref") in supporting_source_refs or (normalized_excerpt and normalized_excerpt in str(unit.get("excerpt") or "").lower())
    ]
    if not candidates:
        return None
    bucket_kinds = {
        "pricing_or_offer_move": {"pricing", "pricing_change", "offer"},
        "messaging_or_positioning_move": {"offer", "positioning", "messaging_shift", "segment"},
        "intercept_or_capture_move": {"opportunity", "closure", "asset_sale", "opening"},
        "proof_or_trust_move": {"proof", "proof_signal"},
        "information_request": {"timing", "segment", "market"},
    }.get(move_bucket, {"market"})
    keywords = {
        token
        for token in re.findall(r"[a-z0-9]+", segment_text.lower())
        if len(token) >= 4 and token not in {"this", "week", "your", "from", "with", "that", "they", "into", "current", "source", "sources"}
    }
    competitor_lc = (competitor or "").lower()

    def unit_score(unit: dict[str, Any]) -> float:
        text = f"{unit.get('label') or ''} {unit.get('excerpt') or ''}".lower()
        score = float(unit.get("confidence") or 0)
        if str(unit.get("unit_kind") or "") in bucket_kinds:
            score += 1.4
        if competitor_lc and competitor_lc in text:
            score += 1.2
        overlap = sum(1 for token in keywords if token in text)
        score += min(1.5, overlap * 0.2)
        return score

    candidates.sort(key=unit_score, reverse=True)
    return candidates[0]


def infer_domain_from_sources(source: SourcePackage, fact_chips: list[dict[str, Any]]) -> str:
    combined = " ".join([source.project_summary, source.raw_text, *[str(chip["label"]) for chip in fact_chips]])
    normalized = combined.lower()
    # "non-club" / "non club" still contains substring "club"; do not classify as youth academy.
    if "non-club" in normalized or re.search(r"\bnon\s+club\b", normalized):
        return "general"
    if any(token in normalized for token in ("academy", " club", "club ", "u14", "families", "intake", "enrollment")):
        return "academy"
    if re.search(r"\bclub\b", normalized):
        return "academy"
    return "general"


def _trusted_competitor_names_from_knowledge(knowledge_rows: list[dict[str, Any]]) -> set[str]:
    trusted: set[str] = set()
    for row in knowledge_rows:
        c = clean_entity(str(row.get("competitor") or ""))
        if c:
            trusted.add(c)
            trusted.add(c.lower())
    return trusted


def _entity_lower_frequency(source_rows: list[dict[str, Any]]) -> dict[str, int]:
    freq: dict[str, int] = {}
    for row in source_rows:
        text = str(row.get("raw_text") or "")
        for ent in extract_named_entities(text):
            n = clean_entity(ent)
            if not n:
                continue
            freq[n.lower()] = freq.get(n.lower(), 0) + 1
    return freq


def _entity_ok_for_competitor_aggregate(
    name: str,
    *,
    trusted: set[str],
    freq: dict[str, int],
) -> bool:
    """Filter naive NER so competitor_count / flashcards are not flooded with common words."""
    n = clean_entity(name)
    if not n:
        return False
    if n in trusted or n.lower() in trusted:
        return True
    words = n.split()
    if len(words) >= 2:
        return not any(w.lower() in ENTITY_NOISE_WORDS for w in words)
    w = words[0]
    wl = w.lower()
    if wl in ENTITY_NOISE_WORDS:
        return False
    if w.isupper():
        return 2 <= len(w) <= 6
    mentions = freq.get(wl, 0)
    if mentions >= 2:
        return len(w) >= 4
    return len(w) >= 8


def build_atomic_facts(
    project_id: str,
    source_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
    knowledge_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_fact(
        fact_type: str,
        fact_key: str,
        fact_value: dict[str, Any],
        *,
        source_ref: str = "",
        clause_text: str | None = None,
        trace_ref: str | None = None,
        confidence: float = 0.6,
    ) -> None:
        key_blob = json.dumps({"t": fact_type, "k": fact_key, "v": fact_value}, sort_keys=True, ensure_ascii=False)
        if key_blob in seen:
            return
        seen.add(key_blob)
        fact_id = str(uuid.uuid4())
        facts.append(
            {
                "fact_id": fact_id,
                "project_id": project_id,
                "source_ref": source_ref,
                "fact_type": fact_type,
                "fact_key": fact_key,
                "fact_value": fact_value,
                "clause_text": clause_text,
                "trace_ref": trace_ref,
                "confidence": round(float(confidence), 2),
            }
        )

    def is_low_quality_entity(value: str) -> bool:
        normalized = clean_entity(value)
        if not normalized:
            return True
        lowered = normalized.lower()
        blocked = {
            "non",
            "none",
            "uploaded file",
            "region unknown",
            "unknown",
            "market",
            "offer",
            "pricing",
            "proof",
            "positioning",
        }
        if lowered in blocked:
            return True
        if len(normalized) < 3:
            return True
        if normalized.endswith(".docx") or normalized.endswith(".pdf"):
            return True
        return False

    # 1) Atomic signal facts (traceable to one observation row)
    for row in observation_rows:
        add_fact(
            "signal",
            str(row.get("signal_type") or "signal"),
            {
                "competitor": row.get("competitor"),
                "region": row.get("region"),
                "summary": row.get("summary"),
            },
            source_ref=str(row.get("source_ref") or ""),
            clause_text=str(row.get("summary") or ""),
            trace_ref=str(row.get("signal_id") or ""),
            confidence=float(row.get("confidence") or 0.58),
        )

    # 2) Competitor entity facts (atomic names; regex NER is noisy — tighten for aggregates)
    trusted_competitors = _trusted_competitor_names_from_knowledge(knowledge_rows)
    entity_freq = _entity_lower_frequency(source_rows)
    competitors = set()
    for row in source_rows:
        text = str(row.get("raw_text") or "")
        for entity in extract_named_entities(text):
            normalized = clean_entity(entity)
            if not normalized or is_low_quality_entity(normalized):
                continue
            if not _entity_ok_for_competitor_aggregate(
                normalized, trusted=trusted_competitors, freq=entity_freq
            ):
                continue
            competitors.add((normalized, str(row.get("source_ref") or "")))
    for row in knowledge_rows:
        competitor = clean_entity(str(row.get("competitor") or ""))
        if competitor:
            competitors.add((competitor, ""))
    for competitor, source_ref in sorted(competitors):
        add_fact(
            "entity",
            "competitor",
            {"name": competitor},
            source_ref=source_ref,
            clause_text=competitor,
            confidence=0.72 if source_ref else 0.64,
        )

    # 3) Aggregate/stat facts derived from atomic facts
    competitor_names = sorted({item[0] for item in competitors})
    add_fact(
        "stat",
        "competitor_count",
        {"value": len(competitor_names), "items": competitor_names[:400]},
        source_ref=source_rows[0]["source_ref"] if source_rows else "",
        confidence=0.8 if competitor_names else 0.42,
    )

    signal_counts: dict[str, int] = {}
    for row in observation_rows:
        signal_type = str(row.get("signal_type") or "unknown")
        signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
    for signal_type, count in sorted(signal_counts.items()):
        add_fact(
            "stat",
            "signal_type_count",
            {"signal_type": signal_type, "value": count},
            source_ref=source_rows[0]["source_ref"] if source_rows else "",
            confidence=0.76,
        )

    raw_joined = " ".join(str(row.get("raw_text") or "") for row in source_rows).lower()
    subscription_present = any(
        token in raw_joined
        for token in ("monthly subscription", "subscription", "recurring", "monthly plan", "membership")
    )
    add_fact(
        "stat",
        "subscription_model_present",
        {"value": bool(subscription_present)},
        source_ref=source_rows[0]["source_ref"] if source_rows else "",
        confidence=0.66 if raw_joined else 0.3,
    )

    return facts


def build_flashcards_from_atomic_facts(
    project_id: str,
    atomic_facts: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    kyc_context: str,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []

    def card(
        insight: str,
        implication: str,
        potential_moves: list[str],
        fact_refs: list[str],
        source_refs: list[str],
        *,
        segment: str = "market",
        competitor: str | None = None,
        channel: str | None = None,
        stable_suffix: str | None = None,
    ) -> None:
        card_id = (
            f"card:{project_id}:heuristic:{stable_suffix}"
            if stable_suffix
            else f"card:{uuid.uuid4()}"
        )
        cards.append(
            {
                "card_id": card_id,
                "project_id": project_id,
                "insight": insight,
                "implication": implication,
                "potential_moves": potential_moves[:3],
                "fact_refs": unique_values(fact_refs),
                "source_refs": unique_values([ref for ref in source_refs if ref]),
                "segment": segment,
                "competitor": competitor,
                "channel": channel or "pricing page",
                "state": "candidate",
            }
        )

    def looks_generic_text(value: str) -> bool:
        lowered = value.lower()
        generic_fragments = (
            "region unknown",
            "uploaded file",
            "non changed pricing",
            "this fact currently contributes",
            "market:",
            "offer:",
            "pricing:",
            "proof:",
            "positioning:",
        )
        return any(fragment in lowered for fragment in generic_fragments)

    competitor_count_fact = next(
        (
            fact
            for fact in atomic_facts
            if fact.get("fact_type") == "stat" and fact.get("fact_key") == "competitor_count"
        ),
        None,
    )
    subscription_fact = next(
        (
            fact
            for fact in atomic_facts
            if fact.get("fact_type") == "stat" and fact.get("fact_key") == "subscription_model_present"
        ),
        None,
    )
    signal_count_facts = [
        fact
        for fact in atomic_facts
        if fact.get("fact_type") == "stat" and fact.get("fact_key") == "signal_type_count"
    ]

    if competitor_count_fact:
        value = int((competitor_count_fact.get("fact_value") or {}).get("value") or 0)
        competitor_items = (competitor_count_fact.get("fact_value") or {}).get("items") or []
        top_examples = [item for item in competitor_items[:6] if isinstance(item, str) and item.strip()][:4]
        if value <= 0:
            insight = _clip_task_copy(
                "We did not lock onto multiple named competitors in this pass—the text may not name firms clearly enough yet.",
                320,
            )
        elif top_examples:
            insight = _clip_task_copy(
                f"We counted about {value} named competitor candidate(s) in your material. "
                f"Examples include: {', '.join(top_examples)}.",
                400,
            )
        else:
            insight = _clip_task_copy(
                f"We counted about {value} named competitor candidate(s); names are still noisy at this confidence.",
                320,
            )
        implication = _clip_task_copy(
            "Automatic name extraction is imperfect—verify spellings and who you actually compete with before acting.",
            260,
        )
        moves = [
            "Cross-check this list against your CRM, win/loss notes, or internal battlecards.",
            "If a name is junk, use Decline and teach so we stop surfacing it.",
            "Add one short source that explicitly lists who you sell against if this feels thin.",
        ]
        card(
            insight=insight,
            implication=implication,
            potential_moves=moves,
            fact_refs=[competitor_count_fact["fact_id"]],
            source_refs=[competitor_count_fact.get("source_ref") or ""],
            segment="competition",
            stable_suffix="competition:competitor_count",
        )

    if subscription_fact:
        value = bool((subscription_fact.get("fact_value") or {}).get("value"))
        insight = _clip_task_copy(
            (
                "Your sources mention subscription-style language—recurring plans, memberships, or monthly packaging."
                if value
                else "We did not see strong subscription or recurring-plan language in this ingest."
            ),
            280,
        )
        implication = _clip_task_copy(
            (
                "Buyers may benchmark you on renewal friction and plan clarity when that language is present."
                if value
                else "If subscriptions matter for you, add copy that states how billing and renewals work."
            ),
            220,
        )
        card(
            insight=insight,
            implication=implication,
            potential_moves=[
                "Compare your public pricing page to what prospects see in onboarding emails.",
                "Spell out trial-to-paid and cancellation in one plain paragraph if it is ambiguous.",
                "Teach the card if this misreads your actual packaging model.",
            ],
            fact_refs=[subscription_fact["fact_id"]],
            source_refs=[subscription_fact.get("source_ref") or ""],
            segment="pricing",
            channel="pricing page",
            stable_suffix="pricing:subscription_model_present",
        )

    for fact in signal_count_facts[:6]:
        data = fact.get("fact_value") or {}
        signal_type = str(data.get("signal_type") or "signal")
        count = int(data.get("value") or 0)
        if count <= 0:
            continue
        kind_label = humanize_evidence_unit_kind(signal_type)
        insight = _clip_task_copy(
            f"In this material we flagged about {count} snippet(s) that read like {kind_label}.",
            280,
        )
        if looks_generic_text(insight):
            continue
        implication = _clip_task_copy(
            "That emphasis shows where the document spends competitive energy—it is a clue, not a final judgment.",
            220,
        )
        card(
            insight=insight,
            implication=implication,
            potential_moves=[
                "Skim your own homepage and pricing page for the same theme—are you answering it?",
                "If this is noise for your market, Decline and teach so we weight it down.",
                "Add a sharper source if you need more than keyword-level confidence.",
            ],
            fact_refs=[fact["fact_id"]],
            source_refs=[fact.get("source_ref") or ""],
            segment="signals",
            stable_suffix=f"signals:{signal_type}",
        )

    if not cards:
        fallback_refs = [fact["fact_id"] for fact in atomic_facts[:3]]
        fallback_source_refs = [fact.get("source_ref") or "" for fact in atomic_facts[:3]]
        ctx = (kyc_context or "").strip()
        ctx_bit = f"{ctx[:220]}… " if len(ctx) > 220 else (f"{ctx} " if ctx else "")
        card(
            insight=_clip_task_copy(
                f"{ctx_bit}We could not shape the usual structured flashcards from this pass yet, "
                f"but {len(atomic_facts)} underlying fact(s) were logged for the project.",
                320,
            ),
            implication=_clip_task_copy(
                "Try a clearer memo, deck excerpt, or pasted page—then re-run so Know More has richer text to judge.",
                220,
            ),
            potential_moves=[
                "Upload material that names competitors, pricing, and proof on one page.",
                "Shorten very long PDFs to the pages you care about before ingest.",
                "Use Decline and teach on any card that misreads you once cards appear.",
            ],
            fact_refs=fallback_refs,
            source_refs=fallback_source_refs,
        )
    return cards


def apply_adaptive_weight_profile(
    project_id: str,
    feedback_rows: list[dict[str, Any]],
    config: WorkerBridgeConfig,
) -> dict[str, float]:
    profile = get_card_weight_profile(project_id, path=config.local_db_path)
    w_conf = float(profile.get("w_confidence", 0.45))
    w_imp = float(profile.get("w_impact", 0.40))
    w_urg = float(profile.get("w_urgency", 0.15))
    sample_count = int(profile.get("sample_count", 0))

    # Lightweight learning loop from usage feedback (phase-2 bootstrap):
    # successful completion => more confidence weight; decline/delete => more urgency/impact pressure.
    for row in feedback_rows[-80:]:
        action = str(row.get("action_type") or row.get("feedback_type") or "")
        if action in {"done", "completed"}:
            w_conf += 0.004
            w_imp += 0.002
        elif action in {"decline_and_replace", "declined", "delete_and_teach"}:
            w_urg += 0.004
            w_imp += 0.002
        elif action in {"hold_for_later", "hold"}:
            w_urg -= 0.002
            w_conf -= 0.001
        sample_count += 1

    # Keep weights positive and normalized.
    w_conf = max(0.05, w_conf)
    w_imp = max(0.05, w_imp)
    w_urg = max(0.05, w_urg)
    total = w_conf + w_imp + w_urg
    normalized = {
        "w_confidence": w_conf / total,
        "w_impact": w_imp / total,
        "w_urgency": w_urg / total,
        "sample_count": sample_count,
    }
    upsert_card_weight_profile(
        project_id,
        normalized["w_confidence"],
        normalized["w_impact"],
        normalized["w_urgency"],
        normalized["sample_count"],
        path=config.local_db_path,
    )
    return normalized


def score_flashcards(
    project_id: str,
    cards: list[dict[str, Any]],
    atomic_facts: list[dict[str, Any]],
    weights: dict[str, float],
) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    fact_lookup = {fact["fact_id"]: fact for fact in atomic_facts}
    scored: list[dict[str, Any]] = []
    for idx, card in enumerate(cards):
        refs = card.get("fact_refs", [])
        ref_facts = [fact_lookup[ref] for ref in refs if ref in fact_lookup]
        confidence = sum(float(f.get("confidence", 0.5)) for f in ref_facts) / max(1, len(ref_facts))
        confidence = max(0.2, min(0.98, confidence))

        # Impact heuristic from segment/channel semantics.
        segment = str(card.get("segment") or "market")
        if segment in {"pricing", "competition"}:
            impact_score = 78.0
            expiry_days = 5
        elif segment in {"signals"}:
            impact_score = 70.0
            expiry_days = 4
        else:
            impact_score = 62.0
            expiry_days = 7
        impact_score = max(30.0, min(98.0, impact_score + (2.0 if len(ref_facts) >= 3 else 0.0)))

        expires_at = now + timedelta(days=expiry_days + idx % 3)
        freshness_score = max(0.05, min(1.0, (expires_at - now).total_seconds() / (10 * 24 * 3600)))
        evidence_strength = max(0.15, min(1.0, len(ref_facts) / 6))

        rank_score = (
            float(weights.get("w_confidence", 0.45)) * confidence
            + float(weights.get("w_impact", 0.40)) * (impact_score / 100.0)
            + float(weights.get("w_urgency", 0.15)) * freshness_score
        )

        card["expires_at"] = expires_at.isoformat().replace("+00:00", "Z")
        scored.append(
            {
                "card_id": card["card_id"],
                "project_id": project_id,
                "confidence": round(confidence, 3),
                "impact_score": round(impact_score, 2),
                "freshness_score": round(freshness_score, 3),
                "evidence_strength": round(evidence_strength, 3),
                "rank_score": round(rank_score, 6),
            }
        )
    return scored


def apply_visibility_top_percent(
    cards: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    percent: float = 0.20,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not cards:
        return [], []
    score_by_card = {score["card_id"]: score for score in scores}
    ranked_cards = sorted(cards, key=lambda c: score_by_card.get(c["card_id"], {}).get("rank_score", 0.0), reverse=True)
    eligible: list[dict[str, Any]] = []
    for card in ranked_cards:
        sc = score_by_card.get(card["card_id"], {})
        if str(card.get("state") or "") == "quarantine":
            continue
        if float(sc.get("rank_score", 0.0)) <= 0.0:
            continue
        eligible.append(card)
    keep = max(1, math.ceil(len(eligible) * percent)) if eligible else 0
    visible_ids = {c["card_id"] for c in eligible[:keep]} if eligible else set()
    visible: list[dict[str, Any]] = []
    all_cards: list[dict[str, Any]] = []
    for card in ranked_cards:
        score = score_by_card.get(card["card_id"], {})
        preset = str(card.get("state") or "")
        if preset == "quarantine":
            final_state = "quarantine"
        elif card["card_id"] in visible_ids:
            final_state = "active"
        else:
            final_state = "suppressed"
        item = {
            **card,
            **score,
            "state": final_state,
        }
        all_cards.append(item)
        if card["card_id"] in visible_ids:
            visible.append(item)
    return all_cards, visible


def infer_segment_kind_for_intel_card(lowered: str) -> str:
    if is_non_commercial_research_context(lowered):
        if _word_boundary_any(lowered, ("proof", "testimonial", "trust", "credential", "integration")):
            return "proof"
        return "positioning"
    if _commercial_pricing_tokens_in_text(lowered):
        return "pricing"
    if _word_boundary_any(lowered, ("proof", "testimonial", "trust", "credential", "integration")):
        return "proof"
    if any(token in lowered for token in ("closure", "sell-off", "asset", "acquisition", "distress")):
        return "opportunity"
    # Homepage/hero/comparison copy is positioning, not commercial "offer" unless real offer tokens match.
    if _commercial_offer_tokens_in_text(lowered):
        return "offer"
    return "positioning"


def _intel_card_text_is_placeholder_blob(insight: str, implication: str) -> bool:
    """True if card copy looks like dummy/placeholder content (do not use clean_entity — it rejects normal prose)."""
    blob = f"{insight} {implication}".lower()
    return any(
        token in blob
        for token in ("uploaded file", "document source", "placeholder", "dummy", "sample competitor")
    )


def intelligence_card_to_synthetic_segment(card: dict[str, Any]) -> dict[str, Any] | None:
    insight = str(card.get("insight") or "").strip()
    implication = str(card.get("implication") or "").strip()
    if not insight or not implication:
        return None
    if _intel_card_text_is_placeholder_blob(insight, implication):
        return None
    comp = str(card.get("competitor") or "").strip()
    segment_text = f"{insight} {implication}".strip()
    if comp and comp.lower() not in segment_text.lower():
        segment_text = f"{segment_text} Competitor context: {comp}."
    if comp and is_placeholder_entity(comp):
        return None
    lowered = segment_text.lower()
    raw_refs = unique_values([str(x) for x in (card.get("fact_refs") or [])] + [str(x) for x in (card.get("source_refs") or [])])
    if not raw_refs:
        cid = card.get("card_id")
        if cid:
            raw_refs = [str(cid)]
    if not raw_refs:
        return None
    source_refs = [str(x) for x in (card.get("source_refs") or [])] or raw_refs[:8]
    cid = card.get("card_id")
    if not cid:
        return None
    return {
        "segment_id": f"intel_card::{cid}",
        "segment_text": segment_text[:8000],
        "segment_kind": infer_segment_kind_for_intel_card(lowered),
        "evidence_refs": raw_refs[:12],
        "source_refs": unique_values(source_refs)[:12],
    }


def backfill_supporting_signals_if_empty(
    task: dict[str, Any],
    *,
    observations: list[dict[str, Any]],
    segment_text: str,
    move_bucket: str,
) -> None:
    if task.get("supporting_signal_scores"):
        return
    competitor = str(task.get("competitor_name") or "").strip() or None
    bundle = select_task_support_signals(
        segment_text=segment_text,
        observations=observations,
        supporting_source_refs=[],
        competitor=competitor,
        move_bucket=move_bucket,
    )
    if not bundle and observations:
        obs_sorted = sorted(
            [o for o in observations if o.get("signal_id")],
            key=lambda o: float(o.get("confidence") or 0),
            reverse=True,
        )[:3]
        bundle = [
            {
                "signal_id": str(o["signal_id"]),
                "relevance_score": max(0.91, round(float(o.get("confidence") or 0.75), 2)),
            }
            for o in obs_sorted
        ]
    if not bundle:
        return
    task["supporting_signal_refs"] = [b["signal_id"] for b in bundle]
    task["supporting_signal_scores"] = bundle


def _canonical_observation_competitor(primary_lc: str, observations: list[dict[str, Any]]) -> str | None:
    for obs in observations:
        oc = str(obs.get("competitor") or "").strip()
        if oc and oc.lower() == primary_lc:
            return oc
    return None


def _intel_segment_preferred_competitor(segment_text: str, observations: list[dict[str, Any]]) -> str | None:
    """When materializing NBA from intelligence cards, prefer the dominant signal competitor if the card text names them."""
    primary_lc = _primary_observation_competitor(observations)
    if not primary_lc:
        return None
    blob = segment_text.lower()
    head = primary_lc.split()[0] if primary_lc else ""
    if primary_lc not in blob and (len(head) < 4 or head not in blob):
        return None
    return _canonical_observation_competitor(primary_lc, observations)


def _primary_observation_competitor(observations: list[dict[str, Any]]) -> str | None:
    counts: dict[str, int] = {}
    for obs in observations:
        comp = str(obs.get("competitor") or "").strip()
        if not comp:
            continue
        key = comp.lower()
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda k: counts[k])


def _task_competitor_aligns_with_primary(task: dict[str, Any], primary_lc: str | None) -> bool:
    if not primary_lc:
        return False
    name = str(task.get("competitor_name") or "").strip().lower()
    if not name:
        return False
    return name in primary_lc or primary_lc in name


def _nba_task_evidence_aligns_primary_competitor(
    task: dict[str, Any],
    observations: list[dict[str, Any]],
    primary_lc: str | None,
) -> bool:
    """True if the task's competitor field or its supporting signals match the dominant observation competitor."""
    if not primary_lc:
        return False
    if _task_competitor_aligns_with_primary(task, primary_lc):
        return True
    by_id = {str(o.get("signal_id") or ""): o for o in observations}
    for sid in task.get("supporting_signal_refs") or []:
        obs = by_id.get(str(sid))
        if not obs:
            continue
        oc = str(obs.get("competitor") or "").strip().lower()
        if oc and (oc == primary_lc or oc in primary_lc or primary_lc in oc):
            return True
    return False


def _nba_task_steps_mention_comparison_surfaces(task: dict[str, Any]) -> bool:
    """Prefer materialized tasks that name concrete buyer-visible comparison assets (pricing page, homepage, proof)."""
    blob = " ".join(task.get("execution_steps") or []).lower()
    return (
        "pricing comparison block" in blob
        or "homepage comparison section" in blob
        or "homepage comparison" in blob
        or "proof blocks" in blob
        or ("comparison section" in blob and "homepage" in blob)
    )


def _intel_card_names_primary_competitor(
    task: dict[str, Any],
    cards_by_id: dict[str, dict[str, Any]],
    primary_lc: str | None,
) -> bool:
    """True if the source intelligence card text names the dominant observation competitor (Know More alignment)."""
    if not primary_lc:
        return False
    cid = str(task.get("intel_card_id") or "")
    card = cards_by_id.get(cid)
    if not card:
        return False
    blob = f"{card.get('insight', '')} {card.get('implication', '')}".lower()
    if primary_lc in blob:
        return True
    head = primary_lc.split()[0]
    return len(head) >= 4 and head in blob


def _nba_observation_competitor_boost(card: dict[str, Any], observations: list[dict[str, Any]]) -> float:
    """Prefer cards that name the same competitors as high-confidence observations (aligns NBA with signals / Know More)."""
    blob = f"{card.get('insight', '')} {card.get('implication', '')} {card.get('competitor', '')}".lower()
    if not blob.strip():
        return 0.0
    boost = 0.0
    ranked_obs = sorted(observations, key=lambda o: float(o.get("confidence") or 0), reverse=True)
    for obs in ranked_obs[:16]:
        comp = str(obs.get("competitor") or "").strip().lower()
        if not comp:
            continue
        if comp in blob:
            boost = max(boost, 0.38)
            continue
        for token in comp.replace(".", " ").split():
            token = token.strip().lower()
            if len(token) >= 4 and token in blob:
                boost = max(boost, 0.28)
                break
    return boost


def build_nba_tasks_from_intelligence_cards(
    cards: list[dict[str, Any]],
    *,
    top_n: int,
    source_package: SourcePackage,
    observations: list[dict[str, Any]],
    knowledge_cards: list[dict[str, Any]],
    fact_chips: list[dict[str, Any]],
    evidence_units: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
    generation_memory_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Turn ranked intelligence cards into judged recommended_tasks (same shape as the segment checklist path)."""
    if not cards or top_n < 1:
        return []
    ranked = sorted(
        cards,
        key=lambda c: (
            float(c.get("rank_score") or 0) + _nba_observation_competitor_boost(c, observations),
            float(c.get("rank_score") or 0),
        ),
        reverse=True,
    )
    pool = ranked[: max(6, top_n * 2)]
    candidates: list[dict[str, Any]] = []
    for card in pool:
        if float(card.get("rank_score") or 0) <= 0.0:
            continue
        if str(card.get("state") or "") == "quarantine":
            continue
        seg = intelligence_card_to_synthetic_segment(card)
        if not seg:
            continue
        task = segment_to_task(
            source_package,
            seg,
            observations,
            knowledge_cards,
            fact_chips,
            evidence_units,
        )
        if not task:
            continue
        move_bucket = str(task.get("move_bucket") or "messaging_or_positioning_move")
        backfill_supporting_signals_if_empty(
            task,
            observations=observations,
            segment_text=str(seg["segment_text"]),
            move_bucket=move_bucket,
        )
        cid = str(card.get("card_id") or "")
        if cid:
            evidence_refs = list(task.get("evidence_refs") or [])
            marker = f"intel_card::{cid}"
            if marker not in evidence_refs:
                task["evidence_refs"] = unique_values([*evidence_refs, marker])
            task["intel_card_id"] = cid
        candidates.append(task)
        if len(candidates) >= 12:
            break
    if len(candidates) < top_n:
        return []
    judged = judge_tasks(candidates[:12], source_package, feedback_rows, generation_memory_rows)
    slot_tasks = judged[:top_n]
    primary_lc = _primary_observation_competitor(observations)
    cards_by_id = {str(c.get("card_id") or ""): c for c in cards if c.get("card_id")}
    if primary_lc and len(slot_tasks) > 1:
        slot_tasks = sorted(
            slot_tasks,
            key=lambda t: (
                _intel_card_names_primary_competitor(t, cards_by_id, primary_lc),
                _nba_task_steps_mention_comparison_surfaces(t),
                _nba_task_evidence_aligns_primary_competitor(t, observations, primary_lc),
                task_priority_score(t, generation_memory_rows),
            ),
            reverse=True,
        )
        now = datetime.now(UTC)
        for index, task in enumerate(slot_tasks, start=1):
            task["rank"] = index
            task["is_next_best_action"] = index == 1
            task["priority_label"] = "critical" if index == 1 else "high" if index == 2 else "normal"
            task["confidence_class"] = (
                "exploratory_action"
                if task.get("task_type") == "exploratory_action"
                else "strong_action"
                if index == 1
                else "moderate_action"
            )
            best_before_days = 2 if index == 1 else 4 if index == 2 else 6
            task["best_before"] = (now + timedelta(days=best_before_days)).date().isoformat()
    return slot_tasks


def build_nba_tasks_from_cards(cards: list[dict[str, Any]], top_n: int = 3) -> list[dict[str, Any]]:
    if not cards:
        return []
    ranked = sorted(cards, key=lambda card: float(card.get("rank_score") or 0), reverse=True)
    selected = ranked[: max(6, top_n * 2)]
    tasks: list[dict[str, Any]] = []
    for card in selected:
        if float(card.get("rank_score") or 0) <= 0.0:
            continue
        if str(card.get("state") or "") == "quarantine":
            continue
        insight = str(card.get("insight") or "").strip()
        implication = str(card.get("implication") or "").strip()
        if not insight or not implication:
            continue
        if _intel_card_text_is_placeholder_blob(insight, implication):
            continue
        comp = str(card.get("competitor") or "").strip()
        if comp and is_placeholder_entity(comp):
            continue
        moves = card.get("potential_moves") or []
        move_title = str(moves[0] if moves else "").strip()
        title = (move_title or insight)[:220]
        if not title or is_placeholder_entity(title):
            continue
        raw_refs = [*card.get("fact_refs", []), *card.get("source_refs", [])]
        evidence_refs = unique_values(raw_refs)[:8]
        if not evidence_refs:
            cid = card.get("card_id")
            if cid:
                evidence_refs = [str(cid)]
        if not evidence_refs:
            continue
        rank = len(tasks) + 1
        tasks.append(
            {
                "rank": rank,
                "title": title,
                "why_now": _clip_task_copy(
                    f"Intelligence card signal: {implication} · card_insight: {insight}",
                    520,
                ),
                "expected_advantage": _clip_task_copy(
                    f"Conversion and revenue positioning linked to card implication: {str(card.get('implication') or insight)}",
                    280,
                ),
                "evidence_refs": evidence_refs,
                "best_before": str(card.get("expires_at") or ""),
                "confidence_class": (
                    "strong_action"
                    if float(card.get("confidence") or 0) >= 0.75
                    else "moderate_action"
                    if float(card.get("confidence") or 0) >= 0.55
                    else "exploratory_action"
                ),
                "supporting_source_refs": card.get("source_refs", []),
            }
        )
        if len(tasks) >= top_n:
            break
    return tasks if len(tasks) == top_n else []


def build_fact_chips(
    source_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
    knowledge_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chips: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_chip(
        category: str,
        label: str,
        confidence: float,
        source_refs: list[str],
        evidence_refs: list[str] | None = None,
    ) -> None:
        normalized_label = normalize_fact_label(label)
        if not normalized_label:
            return
        key = (category, normalized_label.lower())
        if key in seen:
            return
        seen.add(key)
        chips.append(
            {
                "fact_id": f"{category}:{len(chips)+1}",
                "category": category,
                "label": normalized_label,
                "confidence": round(confidence, 2),
                "source_refs": unique_values(source_refs),
                "evidence_refs": unique_values(evidence_refs or []),
            }
        )

    for row in observation_rows:
        phrase = normalize_fact_label(extract_signal_phrase(row["summary"]))
        if not phrase:
            continue
        detail = extract_action_detail(phrase)
        category = observation_to_fact_category(row["signal_type"])
        label = phrase_to_fact_label(category, row["competitor"], phrase, detail, row["region"])
        add_chip(category, label, float(row["confidence"]), [row["source_ref"]], [row["signal_id"]])

    all_text = " ".join(row["raw_text"] for row in source_rows)
    for entity in unique_entities(source_rows, observation_rows, knowledge_rows)[:6]:
        competitor_label = normalize_competitor_fact(entity)
        if competitor_label:
            add_chip("competitor", competitor_label, 0.74, [row["source_ref"] for row in source_rows[:4]])

    clause_sets = [
        ("pricing", ("price", "prices", "pricing", "fee", "plan", "package", "packaging", "bundle", "subscription", "onboarding")),
        ("offer", ("offer", "trial", "discount", "voucher", "scholarship", "free onboarding")),
        ("positioning", ("no engineering", "no-code", "speed", "faster", "implementation", "ai", "automation", "position")),
        ("proof", ("testimonial", "logo", "proof", "case study", "integration", "customer")),
        ("timing", ("this week", "this month", "before", "next intake", "renewal", "last week")),
    ]
    clauses = unique_clauses(source_rows)
    for category, tokens in clause_sets:
        for clause in filter_clauses(clauses, tokens)[:6]:
            label = clause_to_fact_label(category, clause)
            add_chip(category, label, 0.61, source_refs_for_items([clause], source_rows))

    if any(token in all_text.lower() for token in ("pricing", "bundle", "packaging", "subscription", "onboarding")):
        add_chip("pricing", "Pricing bundles, packaging terms, or onboarding friction appear in the source set.", 0.59, [row["source_ref"] for row in source_rows[:4]])
    lowered_all = all_text.lower()
    if _commercial_offer_tokens_in_text(lowered_all):
        add_chip("offer", "Offer-led acquisition pressure appears in the source set.", 0.59, [row["source_ref"] for row in source_rows[:4]])
    if any(token in all_text.lower() for token in ("testimonial", "case study", "customer", "integration", "logo")):
        add_chip("proof", "Proof language appears in the source set and may shape buyer trust.", 0.59, [row["source_ref"] for row in source_rows[:4]])

    for segment in extract_segment_facts(all_text):
        add_chip("segment", segment, 0.63, [row["source_ref"] for row in source_rows[:4]])

    return chips[:18]


def group_fact_chips(fact_chips: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chip in fact_chips:
        grouped.setdefault(str(chip["category"]), []).append(chip)
    return grouped


def flatten_fact_source_refs(fact_chips: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for chip in fact_chips:
        refs.extend(chip.get("source_refs", []))
    return unique_values(refs)


def observation_to_fact_category(signal_type: str) -> str:
    mapping = {
        "pricing_change": "pricing",
        "offer": "offer",
        "proof_signal": "proof",
        "messaging_shift": "positioning",
        "closure": "opportunity",
        "asset_sale": "opportunity",
        "opening": "opportunity",
        "vendor_adoption": "positioning",
    }
    return mapping.get(signal_type, "market")


def phrase_to_fact_label(
    category: str,
    competitor: str,
    phrase: str,
    detail: dict[str, Any],
    region: str,
) -> str:
    if category == "pricing":
        tier = detail.get("tier")
        percent = detail.get("percent")
        if tier and percent:
            return f"{competitor} moved {tier} pricing by {percent} in {humanize_region(region)}."
        if percent:
            return f"{competitor} moved pricing by {percent} in {humanize_region(region)}."
        return f"{competitor} changed pricing or packaging terms in {humanize_region(region)}."
    if category == "offer":
        offer = detail.get("offer") or "offer-led"
        return f"{competitor} is using {offer} acquisition pressure in {humanize_region(region)}."
    if category == "proof":
        return f"{competitor} is leaning on proof signals to win comparison-stage buyers."
    if category == "positioning":
        return f"{competitor} is shifting buyer-facing positioning in {humanize_region(region)}."
    if category == "opportunity":
        return phrase.rstrip(".") + "."
    return phrase.rstrip(".") + "."


def clause_to_fact_label(category: str, clause: str) -> str:
    normalized = normalize_fact_label(clause)
    if not normalized:
        return ""
    if category == "pricing":
        if any(token in normalized.lower() for token in ("bundle", "packaging", "package", "subscription")):
            return "Pricing bundles or packaging structure are part of the current comparison set."
        if "onboarding" in normalized.lower():
            return "Onboarding terms are part of the commercial comparison set."
        return normalized
    if category == "offer":
        nl = normalized.lower()
        if re.search(r"\btrial\b", nl) and not re.search(r"\bclinical\s+trial\b", nl):
            if not (
                re.search(r"\b(jury|bench|criminal|civil|appellate|mistrial|retrial|speedy)\s+trial\b", nl)
                or re.search(r"\btrial\s+(court|attorney|lawyer|judge|date|hearing|day)\b", nl)
            ):
                return "Trial-based acquisition pressure is visible in the source set."
        if any(token in nl for token in ("discount", "voucher", "scholarship")):
            return "Discount-led acquisition pressure is visible in the source set."
        return normalized
    if category == "positioning":
        if any(token in normalized.lower() for token in ("ai", "automation", "intelligence")):
            return "AI or automation-led positioning appears in the source set."
        if any(token in normalized.lower() for token in ("speed", "faster", "implementation", "no code", "no engineering")):
            return "Speed or ease-of-implementation claims appear in the source set."
        return normalized
    if category == "proof":
        if any(token in normalized.lower() for token in ("testimonial", "customer", "case study", "logo")):
            return "Proof language like testimonials or customer examples appears in the source set."
        if "integration" in normalized.lower():
            return "Integration claims are being used as proof in the source set."
        return normalized
    if category == "timing":
        return normalized
    return normalized


def normalize_fact_label(value: str) -> str | None:
    cleaned = " ".join(value.strip().split())
    if not cleaned or len(cleaned) < 12:
        return None
    lowered = cleaned.lower()
    for prefix in (
        "uploaded file:",
        "extracted content:",
        "fetched content:",
        "the document compares",
        "this document compares",
        "the report compares",
        "the document highlights",
        "the document reviews",
        "competitive analysis in",
        "competitive analysis of",
        "industry memo about",
    ):
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip(" :.-")
            lowered = cleaned.lower()
    if not cleaned or len(cleaned) < 12 or is_technical_residue(cleaned):
        return None
    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned[:180]


def normalize_competitor_fact(value: str) -> str | None:
    cleaned = clean_entity(re.sub(r"\bfocus\b$", "", value, flags=re.IGNORECASE).strip(" .:-"))
    if not cleaned:
        return None
    if is_placeholder_entity(cleaned):
        return None
    return cleaned


def is_placeholder_entity(value: str | None) -> bool:
    if value is None:
        return True
    if not str(value).strip():
        return False
    cleaned = clean_entity(value)
    if not cleaned:
        return True
    lowered = cleaned.lower()
    blocked_exact = {
        "uploaded file",
        "document source",
        "manual text",
        "url source",
        "unknown",
        "region unknown",
        "n/a",
        "none",
        "non",
    }
    if lowered in blocked_exact:
        return True
    blocked_substrings = (
        "uploaded file",
        "document source",
        "placeholder",
        "dummy",
        "sample",
    )
    return any(token in lowered for token in blocked_substrings)


def normalize_competitor_for_copy(
    competitor: str,
    *,
    strongest_excerpt: str = "",
    explicit_claim: str | None = None,
) -> str:
    cleaned = clean_entity(competitor) or ""
    if cleaned and not is_placeholder_entity(cleaned):
        return cleaned
    if strongest_excerpt.strip():
        return fallback_competitor_reference(strongest_excerpt=strongest_excerpt, explicit_claim=explicit_claim)
    return "the visible competitor"


def sanitize_signal_summary_for_copy(summary: str) -> str:
    collapsed = " ".join(summary.split())
    collapsed = re.sub(r"uploaded file\s*:\s*[^\n]+", "", collapsed, flags=re.IGNORECASE)
    collapsed = re.sub(r"extracted content\s*:\s*", "", collapsed, flags=re.IGNORECASE)
    collapsed = re.sub(r"\s{2,}", " ", collapsed).strip()
    return collapsed or "A concrete market signal changed in the latest source."


def summarize_market_fact_patterns(fact_chips: list[dict[str, Any]]) -> list[str]:
    categories = {chip["category"] for chip in fact_chips}
    items: list[str] = []
    if "pricing" in categories:
        items.append("Pricing or packaging pressure is visible in the current source set.")
    if "offer" in categories:
        items.append("Offer-led acquisition pressure is visible in the current source set.")
    if "proof" in categories:
        items.append("Proof signals are shaping buyer trust in the current comparison set.")
    if "positioning" in categories:
        items.append("Positioning language is converging around clear buyer-facing claims.")
    if "opportunity" in categories:
        items.append("At least one asymmetric opportunity is visible in the competitive landscape.")
    return items


def extract_segment_facts(text: str) -> list[str]:
    patterns = (
        r"\b(U\d{1,2}\s+(?:families|players|segment))\b",
        r"\b(agency customers?|seo teams?|mid-market buyers?|enterprise buyers?|comparison-stage buyers?|parents)\b",
        r"\b(smb plans?|local families|renewal-stage customers?)\b",
    )
    segments: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = " ".join(match.group(1).split())
            normalized = value.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            segments.append(f"Buyer segment in play: {value}.")
    return segments[:4]


def build_competitive_snapshot(
    knowledge_cards: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
    knowledge_rows: list[dict[str, Any]],
    evidence_units: list[dict[str, Any]],
) -> dict[str, Any]:
    """Workspace contract keeps this object for compatibility; narrative fields stay empty (no pricing / M&A framing)."""
    _ = (knowledge_cards, observation_rows, knowledge_rows, evidence_units)
    return {
        "pricing_position": "",
        "acquisition_strategy_comparison": "",
        "current_weakness": "",
        "active_threats": [],
        "immediate_opportunities": [],
        "reference_competitor": "",
        "risk_level": "",
    }


def build_linked_tasks_by_source(
    job_result: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, list[str]]:
    if job_result.get("status") != "complete":
        return {}
    payload = job_result.get("result_payload", {})
    tasks = payload.get("recommended_tasks")
    if not isinstance(tasks, list):
        return {}
    observation_lookup = {row["signal_id"]: row for row in observations}
    mapping: dict[str, list[str]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        for evidence_ref in task.get("evidence_refs", []):
            observation = observation_lookup.get(evidence_ref)
            if not observation:
                continue
            mapping.setdefault(observation["source_ref"], []).append(task["title"])
    return {source_ref: unique_values(titles) for source_ref, titles in mapping.items()}


def build_source_insights(
    source_rows: list[dict[str, Any]],
    knowledge_cards: list[dict[str, Any]],
    linked_tasks_by_source: dict[str, list[str]],
    evidence_units: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    insights: dict[str, dict[str, Any]] = {}
    for row in source_rows:
        relevant_cards = [card for card in knowledge_cards if row["source_ref"] in card["source_refs"]]
        preferred_card = pick_source_priority_card(relevant_cards)
        source_cluster = pick_best_action_cluster(
            [unit for unit in evidence_units if unit.get("source_ref") == row["source_ref"]]
        )
        takeaway = summarize_source_cluster_takeaway(source_cluster) if source_cluster else (preferred_card["insight"] if preferred_card else "This source adds new market context.")
        impact = summarize_source_cluster_impact(source_cluster) if source_cluster else (preferred_card["implication"] if preferred_card else "This source strengthens what the system knows about the market.")
        confidence = max((float(card["confidence"]) for card in relevant_cards), default=0.52)
        insights[row["source_ref"]] = {
            "key_takeaway": takeaway,
            "business_impact": impact,
            "linked_tasks": linked_tasks_by_source.get(row["source_ref"], []),
            "confidence": round(confidence, 2),
        }
    return insights


def derive_source_takeaway(row: dict[str, Any], knowledge_cards: list[dict[str, Any]], evidence_units: list[dict[str, Any]]) -> str:
    source_cluster = pick_best_action_cluster(
        [unit for unit in evidence_units if unit.get("source_ref") == row["source_ref"]]
    )
    if source_cluster:
        return summarize_source_cluster_takeaway(source_cluster)
    relevant_cards = [card for card in knowledge_cards if row["source_ref"] in card["source_refs"]]
    relevant_card = pick_source_priority_card(relevant_cards)
    return relevant_card["insight"] if relevant_card else "This source adds context to the local market picture."


def derive_source_business_impact(row: dict[str, Any], knowledge_cards: list[dict[str, Any]], evidence_units: list[dict[str, Any]]) -> str:
    source_cluster = pick_best_action_cluster(
        [unit for unit in evidence_units if unit.get("source_ref") == row["source_ref"]]
    )
    if source_cluster:
        return summarize_source_cluster_impact(source_cluster)
    relevant_cards = [card for card in knowledge_cards if row["source_ref"] in card["source_refs"]]
    relevant_card = pick_source_priority_card(relevant_cards)
    return relevant_card["implication"] if relevant_card else "Use this source to improve future recommendation quality."


def derive_source_confidence(signal_count: int, knowledge_count: int) -> float:
    return min(0.45 + (signal_count * 0.08) + (knowledge_count * 0.03), 0.88)


def pick_source_priority_card(relevant_cards: list[dict[str, Any]]) -> dict[str, Any] | None:
    preferred_ids = [
        "pricing_packaging",
        "offer_positioning",
        "competitors_detected",
        "proof_signals",
        "market_summary",
        "open_questions",
    ]
    for knowledge_id in preferred_ids:
        match = next((card for card in relevant_cards if card["knowledge_id"] == knowledge_id), None)
        if match:
            return match
    return relevant_cards[0] if relevant_cards else None


def summarize_source_cluster_takeaway(cluster: dict[str, Any]) -> str:
    competitor = str(cluster.get("competitor") or "A competitor").strip()
    asset = str(cluster.get("asset") or "").strip()
    channel = str(cluster.get("channel") or "").strip()
    claim = str(cluster.get("claim") or "").strip()
    if asset and channel and claim:
        return f"{competitor} is pressing on {channel} with {asset} shaped around the {claim} claim."
    if asset and channel:
        return f"{competitor} is making {channel} more competitive through {asset}."
    if claim:
        return f"{competitor} is using the {claim} claim in the current comparison set."
    excerpt = str(cluster.get("excerpt") or "").strip()
    if excerpt:
        return excerpt[:220]
    return "This source adds new market context."


def summarize_source_cluster_impact(cluster: dict[str, Any]) -> str:
    competitor = str(cluster.get("competitor") or "a competitor").strip()
    asset = str(cluster.get("asset") or "").strip()
    channel = str(cluster.get("channel") or "").strip()
    claim = str(cluster.get("claim") or "").strip()
    if asset and channel and claim:
        return f"If you do not answer {competitor}'s {claim} claim in the {channel}, your current {asset} can look weaker in live comparisons."
    if asset and channel:
        return f"This source changes what you may need to show in the {channel}, because {competitor} is already making that asset visible."
    if claim:
        return f"This source changes the comparison language buyers may hear first, because {competitor} is already using the {claim} claim."
    return "This source strengthens what the system knows about the market."


def cluster_specificity_score(cluster: dict[str, Any]) -> float:
    score = float(cluster.get("confidence") or 0)
    if cluster.get("competitor"):
        score += 1.0
    if cluster.get("claim"):
        score += 1.0
    if cluster.get("asset"):
        score += 0.8
    if cluster.get("channel"):
        score += 0.6
    if cluster.get("section"):
        score += 0.4
    score += min(0.5, float(cluster.get("cluster_size") or 0) * 0.1)
    return score


def pick_best_action_cluster(units: list[dict[str, Any]]) -> dict[str, Any] | None:
    clusters = cluster_units_by_action_shape(units)
    if not clusters:
        return None
    clusters.sort(key=cluster_specificity_score, reverse=True)
    return clusters[0]


def parse_json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    return []


_DEBUG_POTENTIAL_MOVE_PREFIX = re.compile(r"^\s*row\[\d+\]\s*=\s*", re.IGNORECASE)


def _strip_debug_potential_move_prefix(line: str) -> str:
    s = str(line).strip()
    return _DEBUG_POTENTIAL_MOVE_PREFIX.sub("", s, count=1).strip()


def _looks_like_debug_potential_move_line(line: str) -> bool:
    return bool(_DEBUG_POTENTIAL_MOVE_PREFIX.match(str(line).strip()))


def normalize_operator_potential_moves(corrected: Any, fresh: list[str]) -> list[str]:
    """Use feedback-corrected moves when sane; never emit row[]= debug lines."""
    fresh_list = [str(x).strip() for x in fresh if str(x).strip()]
    parsed = parse_json_list(corrected) if corrected is not None else []
    if not parsed:
        return fresh_list[:3]

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in parsed:
        line = str(raw).strip()
        if not line:
            continue
        if _looks_like_debug_potential_move_line(line):
            line = _strip_debug_potential_move_prefix(line)
        if not line or _looks_like_debug_potential_move_line(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(_clip_task_copy(line, 220))
        if len(cleaned) >= 3:
            break

    return cleaned[:3] if cleaned else fresh_list[:3]


def knowledge_card(
    knowledge_id: str,
    title: str,
    summary: str,
    items: list[str],
    insight: str,
    implication: str,
    potential_moves: list[str],
    evidence_rows: list[dict[str, Any]],
    source_refs: list[str],
    confidence: float,
    feedback_lookup: dict[str, dict[str, Any]],
    support_count: int = 0,
    strongest_excerpt: str | None = None,
) -> dict[str, Any]:
    feedback = feedback_lookup.get(knowledge_id)
    feedback_original_payload = feedback.get("original_payload") if feedback else None
    original_payload = {
        "title": title,
        "summary": summary,
        "items": items,
        "insight": insight,
        "implication": implication,
        "potential_moves": potential_moves,
    }
    return {
        "knowledge_id": knowledge_id,
        "title": feedback.get("corrected_title") if feedback and feedback.get("corrected_title") else title,
        "summary": feedback.get("corrected_summary") if feedback and feedback.get("corrected_summary") else summary,
        "items": feedback.get("corrected_items") if feedback and feedback.get("corrected_items") else items,
        # Always use freshly built insight from evidence (do not pin to original_payload.insight—that
        # snapshot freezes obsolete debug-era copy after any feedback row exists for this knowledge_id).
        "insight": (str((feedback or {}).get("corrected_insight") or "").strip() or insight),
        "implication": feedback.get("corrected_implication") if feedback and feedback.get("corrected_implication") else implication,
        "potential_moves": normalize_operator_potential_moves(
            feedback.get("corrected_potential_moves") if feedback else None,
            potential_moves,
        ),
        "source_refs": unique_values(source_refs),
        "evidence_refs": unique_values([row["signal_id"] for row in evidence_rows]),
        "confidence": round(confidence, 2),
        "support_count": support_count,
        "strongest_excerpt": strongest_excerpt,
        "annotation_status": feedback["status"] if feedback else "pending",
        "confidence_source": feedback.get("confidence_source") if feedback and feedback.get("confidence_source") else "extracted",
        "audit": {
            "original_value": feedback.get("original_payload") if feedback and feedback.get("original_payload") else original_payload,
            "user_modification": {
                "title": feedback.get("corrected_title"),
                "summary": feedback.get("corrected_summary"),
                "items": feedback.get("corrected_items"),
                "implication": feedback.get("corrected_implication"),
                "potential_moves": feedback.get("corrected_potential_moves"),
            }
            if feedback
            else None,
            "timestamp": feedback.get("updated_at") if feedback else None,
        },
    }


def unique_clauses(source_rows: list[dict[str, Any]]) -> list[str]:
    clauses: list[str] = []
    seen: set[str] = set()
    for row in source_rows:
        for clause in extract_clauses(row["raw_text"]):
            normalized = clause.strip()
            if len(normalized) < 16:
                continue
            if is_technical_residue(normalized):
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            clauses.append(normalized)
    return clauses


def unique_entities(
    source_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
    knowledge_rows: list[dict[str, Any]],
) -> list[str]:
    values: list[str] = [row["competitor"] for row in observation_rows if row.get("competitor")]
    values.extend(row["competitor"] for row in knowledge_rows if row.get("competitor"))
    for row in source_rows:
        values.extend(extract_named_entities(row["raw_text"]))
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = clean_entity(value)
        if not normalized:
            continue
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        cleaned.append(normalized)
    return cleaned[:12]


def build_evidence_units(
    project_id: str,
    source_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
    fact_chips: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    seen: set[str] = set()
    source_map = {row["source_ref"]: row for row in source_rows}

    def add_unit(
        *,
        source_ref: str,
        unit_kind: str,
        label: str,
        excerpt: str,
        confidence: float,
    ) -> None:
        detail = extract_action_detail(label)
        competitor = infer_segment_competitor(label, SourcePackage(
            project_id=project_id,
            source_kind=source_map.get(source_ref, {}).get("source_kind", "manual_text"),
            project_summary=source_map.get(source_ref, {}).get("project_summary", "managed_on_worker"),
            raw_text=source_map.get(source_ref, {}).get("raw_text", label),
            source_ref=source_ref,
            competitor=source_map.get(source_ref, {}).get("competitor"),
            region=source_map.get(source_ref, {}).get("region"),
        ))
        channel = infer_primary_channel("academy" if "enrollment" in excerpt.lower() else "general", excerpt.lower())
        segment = next((fact.replace("Buyer segment in play: ", "").replace(".", "") for fact in extract_segment_facts(excerpt)), None)
        key = f"{source_ref}|{unit_kind}|{label}".lower()
        if key in seen:
            return
        seen.add(key)
        units.append(
            {
                "unit_id": f"{project_id}::{abs(hash((source_ref, unit_kind, label)))}",
                "project_id": project_id,
                "source_ref": source_ref,
                "unit_kind": unit_kind,
                "label": label,
                "excerpt": excerpt[:320],
                "competitor": competitor,
                "segment": segment,
                "channel": detail.get("channel") or channel,
                "section": detail.get("section"),
                "asset": detail.get("asset"),
                "claim": detail.get("claim"),
                "timing": detail.get("timeframe"),
                "confidence": round(confidence, 2),
            }
        )

    for chip in fact_chips:
        for source_ref in chip.get("source_refs", []) or ["unknown_source"]:
            excerpt = source_map.get(source_ref, {}).get("raw_text", chip["label"])
            add_unit(
                source_ref=source_ref,
                unit_kind=str(chip["category"]),
                label=str(chip["label"]),
                excerpt=str(excerpt),
                confidence=float(chip.get("confidence", 0.6)),
            )

    for row in observation_rows:
        add_unit(
            source_ref=row["source_ref"],
            unit_kind=str(row["signal_type"]),
            label=str(row["summary"]),
            excerpt=str(row["summary"]),
            confidence=float(row.get("confidence", 0.7)),
        )

    for row in source_rows:
        for clause in extract_clauses(str(row.get("raw_text") or "")):
            normalized_clause = clause.strip()
            if len(normalized_clause) < 32 or is_technical_residue(normalized_clause):
                continue
            detail = extract_action_detail(normalized_clause)
            if not any(detail.get(key) for key in ("channel", "section", "asset", "claim", "offer", "timeframe")):
                continue
            add_unit(
                source_ref=row["source_ref"],
                unit_kind="source_clause",
                label=normalize_fact_label(normalized_clause) or normalized_clause,
                excerpt=normalized_clause,
                confidence=0.58,
            )

    return units[:400]


def group_evidence_units(units: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        grouped.setdefault(str(unit["unit_kind"]), []).append(unit)
    return grouped


def flatten_unit_source_refs(units: list[dict[str, Any]]) -> list[str]:
    return unique_values([str(unit["source_ref"]) for unit in units if unit.get("source_ref")])


def prettify_auto_research_excerpt(text: str) -> str:
    """Turn internal 'Auto Research URL/Title/Content' blobs into a short operator-facing line."""
    t = text.strip()
    if not t:
        return ""
    if "Auto Research URL:" in t:
        url_m = re.search(r"Auto Research URL:\s*(\S+)", t)
        title_m = re.search(r"Auto Research Title:\s*(.+)", t)
        url = url_m.group(1).strip() if url_m else ""
        title = title_m.group(1).strip() if title_m else ""
        title = title.split("\n")[0].strip()
        if title and url:
            return f"We matched a public page titled “{title}” ({url})."
        if url:
            return f"We matched a public page ({url})."
    return t


def strongest_unit_excerpt(
    units: list[dict[str, Any]],
    *,
    allow_operator_unfriendly_fallback: bool = True,
) -> str | None:
    if not units:
        return None

    def _operator_friendly(u: dict[str, Any]) -> bool:
        blob = f"{u.get('excerpt') or ''} {u.get('label') or ''}".lower().strip()
        if not blob:
            return True
        if is_legal_or_evidentiary_context(blob):
            return False
        if is_non_commercial_research_context(blob):
            return False
        return True

    preferred = [u for u in units if _operator_friendly(u)]
    if preferred:
        pool = preferred
    elif allow_operator_unfriendly_fallback:
        pool = units
    else:
        return None

    strongest = max(pool, key=lambda unit: float(unit.get("confidence") or 0))
    excerpt = str(strongest.get("excerpt") or "").strip()
    if not excerpt:
        return None
    readable = prettify_auto_research_excerpt(excerpt)
    return _clip_task_copy(readable, 260) if readable else None


def unique_units_by_label(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for unit in sorted(units, key=lambda item: float(item.get("confidence") or 0), reverse=True):
        key = str(unit.get("label") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(unit)
    return result


def unit_cluster_title(unit: dict[str, Any]) -> str:
    asset = str(unit.get("asset") or "").strip()
    section = str(unit.get("section") or "").strip()
    channel = str(unit.get("channel") or "").strip()
    claim = str(unit.get("claim") or "").strip()
    if asset and channel:
        return f"{asset.title()} on {channel.title()}"
    if section and channel:
        return f"{section.title()} on {channel.title()}"
    if claim:
        return f"{claim.title()} pressure"
    if channel:
        return f"{channel.title()} move"
    return humanize_fact_category(str(unit.get("unit_kind") or "evidence"))


def humanize_evidence_unit_kind(kind: str) -> str:
    k = (kind or "").strip().lower()
    return {
        "offer": "offer- or trial-style conversion pressure",
        "pricing": "pricing or packaging pressure",
        "pricing_change": "pricing change signals",
        "pricing_packaging": "pricing or packaging",
        "positioning": "positioning or messaging",
        "proof": "proof or trust signals",
        "proof_signal": "proof or trust signals",
        "messaging_shift": "messaging or positioning shift",
        "opportunity": "market shift or opportunity",
        "closure": "closure or exit signals",
        "asset_sale": "asset or clearance signals",
        "opening": "launch or new-program signals",
        "vendor_adoption": "vendor or platform adoption",
        "segment": "buyer- or segment-focused language",
    }.get(k, "competitive signal")


def cluster_units_by_action_shape(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        key = "|".join(
            [
                str(unit.get("unit_kind") or ""),
                str(unit.get("asset") or ""),
                str(unit.get("section") or ""),
                str(unit.get("channel") or ""),
                str(unit.get("claim") or ""),
            ]
        ).lower()
        if not key.replace("|", "").strip():
            continue
        clusters.setdefault(key, []).append(unit)

    clustered: list[dict[str, Any]] = []
    for cluster_units in clusters.values():
        cluster_units.sort(key=lambda unit: float(unit.get("confidence") or 0), reverse=True)
        strongest = dict(cluster_units[0])
        strongest["cluster_size"] = len(cluster_units)
        strongest["label"] = unit_cluster_title(strongest)
        clustered.append(strongest)
    clustered.sort(key=lambda unit: (float(unit.get("confidence") or 0), int(unit.get("cluster_size") or 0)), reverse=True)
    return clustered


def action_aware_card_items(units: list[dict[str, Any]], fallback_labels: list[str], limit: int = 5) -> list[str]:
    action_units = cluster_units_by_action_shape(units)
    if action_units:
        items: list[str] = []
        for unit in action_units[:limit]:
            excerpt = str(unit.get("excerpt") or "").strip()
            label = str(unit.get("label") or "").strip()
            if excerpt and excerpt.lower() != label.lower():
                items.append(f"{label}: {excerpt}")
            elif label:
                items.append(label)
        if items:
            return items
    return fallback_labels[:limit]


def build_unit_cluster_segments(
    *,
    project_id: str,
    evidence_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    clusters: dict[str, list[dict[str, Any]]] = {}
    for unit in evidence_units:
        cluster_key = "|".join(
            [
                str(unit.get("unit_kind") or ""),
                str(unit.get("asset") or ""),
                str(unit.get("section") or ""),
                str(unit.get("channel") or ""),
                str(unit.get("claim") or ""),
            ]
        ).lower()
        if not cluster_key.replace("|", "").strip():
            continue
        clusters.setdefault(cluster_key, []).append(unit)

    segments: list[dict[str, Any]] = []
    for cluster_units in clusters.values():
        cluster_units.sort(key=lambda unit: float(unit.get("confidence") or 0), reverse=True)
        strongest = cluster_units[0]
        source_refs = flatten_unit_source_refs(cluster_units)
        segment_text = str(strongest.get("excerpt") or strongest.get("label") or "").strip()
        if not segment_text:
            continue
        unit_id = str(strongest.get("unit_id") or "")
        segments.append(
            {
                "segment_id": f"{project_id}::unit-cluster::{abs(hash((unit_id, strongest.get('asset'), strongest.get('claim'), strongest.get('channel'))))}",
                "segment_kind": str(strongest.get("unit_kind") or "evidence_cluster"),
                "title": unit_cluster_title(strongest),
                "segment_text": segment_text,
                "source_refs": source_refs,
                "evidence_refs": [f"unit::{str(unit.get('unit_id') or '')}" for unit in cluster_units if unit.get("unit_id")],
                "importance": round(min(0.97, 0.45 + max(float(unit.get("confidence") or 0) for unit in cluster_units)), 2),
                "confidence": round(float(strongest.get("confidence") or 0), 2),
            }
        )
    return segments


def market_summary_insight(market_units: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> str:
    if not market_units:
        return _clip_task_copy(
            "We do not yet have enough structured evidence lines to summarize the market—try another upload "
            f"or a clearer memo. ({len(source_rows)} source(s) ingested.)",
            280,
        )
    clusters = cluster_units_by_action_shape(market_units)
    if clusters:
        lead = summarize_market_cluster_item(clusters[0])
        return _clip_task_copy(
            f"{lead} In total we are holding {len(market_units)} evidence line(s) under this summary.",
            320,
        )
    top = market_units[0]
    kind = humanize_evidence_unit_kind(str(top.get("unit_kind") or ""))
    excerpt = prettify_auto_research_excerpt(str(top.get("excerpt") or top.get("label") or "").strip())
    if excerpt:
        return _clip_task_copy(f"The strongest single read is {kind}: {excerpt}", 300)
    return _clip_task_copy(f"The strongest single read is {kind}, based on the current extract.", 220)


def market_summary_implication(market_units: list[dict[str, Any]]) -> str:
    if not market_units:
        return (
            "Treat the workspace as provisional until richer sources land; you can still Decline and teach any card that "
            "misreads you."
        )
    kinds = {str(u.get("unit_kind") or "").lower() for u in market_units[:24]}
    if kinds & {"offer", "pricing", "pricing_change", "pricing_packaging"}:
        return (
            "Buyers will compare trials, packaging, and numbers they can see—check that your site and talk track answer "
            "those comparisons directly."
        )
    if kinds & {"proof", "proof_signal"}:
        return (
            "Trust and proof are loud in this material; if your side is quieter, it will show up in live bake-offs."
        )
    return (
        "Use this card as a working read of what the ingested text emphasizes—not a final judgment on your strategy."
    )


def select_market_summary_items(market_units: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> list[str]:
    clusters = cluster_units_by_action_shape(market_units)
    if not clusters:
        return []

    selected: list[str] = []
    seen_kinds: set[str] = set()
    for cluster in sorted(clusters, key=cluster_specificity_score, reverse=True):
        unit_kind = str(cluster.get("unit_kind") or "")
        summary = summarize_market_cluster_item(cluster)
        if not summary:
            continue
        if unit_kind in seen_kinds and len(selected) >= 3:
            continue
        seen_kinds.add(unit_kind)
        selected.append(summary)
        if len(selected) >= 4:
            break

    if not selected and source_rows:
        return [f"{len(source_rows)} ingested source{'s' if len(source_rows) != 1 else ''} are shaping the current knowledge state."]
    return selected


def summarize_market_cluster_item(cluster: dict[str, Any]) -> str:
    kind_phrase = humanize_evidence_unit_kind(str(cluster.get("unit_kind") or ""))
    comp = clean_entity(str(cluster.get("competitor") or "").strip())
    channel = str(cluster.get("channel") or "").strip()
    asset = str(cluster.get("asset") or "").strip()
    section = str(cluster.get("section") or "").strip()
    claim = str(cluster.get("claim") or "").strip()
    n = max(1, int(cluster.get("cluster_size") or 1))
    label = str(cluster.get("label") or "").strip()

    where_bits: list[str] = []
    if channel:
        where_bits.append(channel)
    if section and section.lower() != channel.lower():
        where_bits.append(section)
    elif asset and asset.lower() != channel.lower():
        where_bits.append(asset)
    where = ", ".join(where_bits) if where_bits else "the ingested material"

    who = f" involving {comp}" if comp else ""
    claim_bit = f" The text also stresses “{claim}”." if claim and claim.lower() not in where.lower() else ""

    if n > 1:
        strength = f" ({n} supporting snippets cluster this way.)"
    else:
        strength = ""

    sentence = f"We read {kind_phrase}{who}, concentrated around {where}.{claim_bit}{strength}"
    if label and label.lower() not in sentence.lower():
        sentence = f"{sentence} ({label})"
    return _clip_task_copy(" ".join(sentence.split()), 320)


def normalize_item_signature(item: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", item.lower()).strip()


def dedupe_card_items(items: list[str], blocked_signatures: set[str]) -> list[str]:
    deduped: list[str] = []
    seen = set(blocked_signatures)
    for item in items:
        signature = normalize_item_signature(item)
        if not signature or signature in seen:
            continue
        seen.add(signature)
        deduped.append(item)
    return deduped


def competitor_card_items(
    evidence_units: list[dict[str, Any]],
    competitor_facts: list[dict[str, Any]],
    entities: list[str],
) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for unit in evidence_units:
        competitor = clean_entity(str(unit.get("competitor") or ""))
        if competitor and competitor.lower() not in seen:
            seen.add(competitor.lower())
            values.append(competitor)
    for fact in competitor_facts:
        label = clean_entity(str(fact.get("label") or ""))
        if label and label.lower() not in seen:
            seen.add(label.lower())
            values.append(label)
    for entity in entities:
        label = clean_entity(entity)
        if label and label.lower() not in seen:
            seen.add(label.lower())
            values.append(label)
    return values[:6]


def source_refs_for_competitor_items(items: list[str], evidence_units: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    lowered_items = {item.lower() for item in items}
    for unit in evidence_units:
        competitor = str(unit.get("competitor") or "").lower()
        if competitor and competitor in lowered_items:
            refs.append(str(unit.get("source_ref") or ""))
    return unique_values(refs)


def strongest_competitor_excerpt(items: list[str], evidence_units: list[dict[str, Any]]) -> str | None:
    lowered_items = {item.lower() for item in items}
    matched = [unit for unit in evidence_units if str(unit.get("competitor") or "").lower() in lowered_items]
    return strongest_unit_excerpt(matched, allow_operator_unfriendly_fallback=False)


def missing_evidence_categories(units: list[dict[str, Any]]) -> list[str]:
    categories = {str(unit.get("unit_kind") or "") for unit in units}
    gaps: list[str] = []
    if not categories.intersection({"pricing", "pricing_change"}):
        gaps.append("Pricing or packaging evidence is light—add pages that spell out plans, fees, or bundles.")
    if not categories.intersection({"offer", "positioning", "messaging_shift"}):
        gaps.append("Offer or positioning language is thin—add copy about trials, packaging, or how you differentiate.")
    if not categories.intersection({"proof", "proof_signal"}):
        gaps.append("Proof or trust signals are thin—add testimonials, logos, metrics, or case-style claims.")
    return gaps


def strongest_offer_hint(text: str) -> str | None:
    lowered = text.lower()
    if is_legal_or_evidentiary_context(lowered) or is_non_commercial_research_context(lowered):
        return None
    if re.search(r"\btrial\b", lowered) and not re.search(r"\bclinical\s+trial\b", lowered):
        if re.search(
            r"\b(jury|bench|criminal|civil|appellate|mistrial|retrial|speedy)\s+trial\b",
            lowered,
        ) or re.search(r"\btrial\s+(court|attorney|lawyer|judge|date|hearing|day)\b", lowered):
            pass
        else:
            return "trial"
    if re.search(r"\bdiscount\b", lowered):
        return "discount"
    if "testimonial" in lowered or "proof" in lowered:
        return "proof"
    if "integration" in lowered:
        return "integration"
    return None


def infer_task_move_bucket(segment_kind: str, lowered_text: str) -> str:
    if segment_kind in {"pricing", "pricing_packaging"} or _commercial_pricing_tokens_in_text(lowered_text):
        return "pricing_or_offer_move"
    if segment_kind in {"proof"} or _word_boundary_any(lowered_text, ("proof", "testimonial", "integration", "trust")):
        return "proof_or_trust_move"
    if (
        segment_kind in {"offer", "offer_positioning", "positioning"}
        or _commercial_offer_tokens_in_text(lowered_text)
        or _word_boundary_any(lowered_text, ("positioning", "message"))
    ):
        return "messaging_or_positioning_move"
    if segment_kind in {"opportunity", "closure", "asset_sale"} or any(token in lowered_text for token in ("closure", "sell-off", "asset", "opportunity", "distress")):
        return "intercept_or_capture_move"
    if segment_kind in {"open_questions", "timing"} or any(token in lowered_text for token in ("region", "unknown", "need", "add one source", "gap", "confirm")):
        return "information_request"
    return "proof_or_trust_move" if any(token in lowered_text for token in ("proof", "testimonial", "integration", "trust")) else "messaging_or_positioning_move"


def score_task_supporting_source(
    *,
    source_ref: str,
    segment_text: str,
    evidence_units: list[dict[str, Any]],
    competitor: str | None,
    move_bucket: str,
) -> tuple[float, str | None]:
    relevant_units = [unit for unit in evidence_units if unit.get("source_ref") == source_ref]
    if not relevant_units:
        return 0.0, None

    keywords = {
        token
        for token in re.findall(r"[a-z0-9]+", segment_text.lower())
        if len(token) >= 4 and token not in {"this", "week", "your", "from", "with", "that", "they", "into", "current", "source", "sources"}
    }
    bucket_kinds = {
        "pricing_or_offer_move": {"pricing", "pricing_change", "offer"},
        "messaging_or_positioning_move": {"offer", "positioning", "messaging_shift", "segment"},
        "intercept_or_capture_move": {"opportunity", "closure", "asset_sale", "opening"},
        "proof_or_trust_move": {"proof", "proof_signal"},
        "information_request": {"timing", "segment", "market"},
    }.get(move_bucket, {"market"})

    best_excerpt: str | None = None
    best_score = 0.0
    aggregate = 0.0
    competitor_lc = (competitor or "").lower()
    for unit in relevant_units:
        text = f"{unit.get('label') or ''} {unit.get('excerpt') or ''}".lower()
        score = float(unit.get("confidence") or 0)
        if competitor_lc and competitor_lc in text:
            score += 1.5
        if str(unit.get("unit_kind") or "") in bucket_kinds:
            score += 1.2
        overlap = sum(1 for token in keywords if token in text)
        score += min(2.0, overlap * 0.25)
        aggregate += score
        if score > best_score:
            best_score = score
            best_excerpt = str(unit.get("excerpt") or unit.get("label") or "").strip()[:220] or None

    return aggregate / max(1, len(relevant_units)), best_excerpt


def select_task_support_bundle(
    *,
    segment_text: str,
    segment_source_refs: list[str],
    evidence_units: list[dict[str, Any]],
    competitor: str | None,
    move_bucket: str,
) -> tuple[list[dict[str, Any]], str | None]:
    scored: list[tuple[str, float, str | None]] = []
    for source_ref in unique_values(segment_source_refs):
        score, excerpt = score_task_supporting_source(
            source_ref=source_ref,
            segment_text=segment_text,
            evidence_units=evidence_units,
            competitor=competitor,
            move_bucket=move_bucket,
        )
        if score > 0:
            scored.append((source_ref, score, excerpt))

    scored.sort(key=lambda item: item[1], reverse=True)
    filtered = [item for item in scored if item[1] >= 0.85]
    chosen = filtered[:3] if filtered else scored[:2]
    strongest_excerpt = chosen[0][2] if chosen else None
    return [
        {
            "source_ref": item[0],
            "relevance_score": round(float(item[1]), 2),
            "strongest_excerpt": item[2],
        }
        for item in chosen
    ], strongest_excerpt


def score_task_supporting_signal(
    *,
    observation: dict[str, Any],
    segment_text: str,
    competitor: str | None,
    move_bucket: str,
) -> float:
    text = str(observation.get("summary") or "").lower()
    score = float(observation.get("confidence") or 0)
    competitor_lc = (competitor or "").lower()
    if competitor_lc and competitor_lc in text:
        score += 1.2
    signal_type = str(observation.get("signal_type") or "")
    bucket_signal_map = {
        "pricing_or_offer_move": {"pricing_change", "offer"},
        "messaging_or_positioning_move": {"offer", "messaging_shift", "vendor_adoption"},
        "intercept_or_capture_move": {"closure", "asset_sale", "opening"},
        "proof_or_trust_move": {"proof_signal"},
        "information_request": {"pricing_change", "offer", "proof_signal", "messaging_shift"},
    }
    if signal_type in bucket_signal_map.get(move_bucket, set()):
        score += 1.0
    keywords = {token for token in re.findall(r"[a-z0-9]+", segment_text.lower()) if len(token) >= 4}
    overlap = sum(1 for token in keywords if token in text)
    score += min(1.5, overlap * 0.2)
    return score


def select_task_support_signals(
    *,
    segment_text: str,
    observations: list[dict[str, Any]],
    supporting_source_refs: list[str],
    competitor: str | None,
    move_bucket: str,
) -> list[dict[str, Any]]:
    candidates = [
        observation
        for observation in observations
        if not supporting_source_refs or observation.get("source_ref") in supporting_source_refs
    ]
    scored = sorted(
        (
            (
                str(observation.get("signal_id") or ""),
                score_task_supporting_signal(
                    observation=observation,
                    segment_text=segment_text,
                    competitor=competitor,
                    move_bucket=move_bucket,
                ),
            )
            for observation in candidates
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        {"signal_id": signal_id, "relevance_score": round(float(score), 2)}
        for signal_id, score in scored
        if signal_id and score >= 0.9
    ][:3]


def select_task_support_segments(
    *,
    segment: dict[str, Any],
    move_bucket: str,
    competitor: str | None,
) -> list[dict[str, Any]]:
    segment_id = str(segment.get("segment_id") or "")
    refs = [{"segment_id": segment_id, "relevance_score": 1.8 if competitor else 1.2}] if segment_id else []
    if move_bucket == "information_request":
        refs.extend(
            {
                "segment_id": str(ref).replace("segment::", "", 1),
                "relevance_score": 1.0,
            }
            for ref in segment.get("evidence_refs") or []
            if str(ref).startswith("segment::")
        )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in refs:
        segment_ref = str(item.get("segment_id") or "")
        if not segment_ref or segment_ref in seen:
            continue
        seen.add(segment_ref)
        deduped.append(item)
    return deduped[:2] if competitor and segment_id else deduped[:1]


def synthesize_task_why_now(
    *,
    move_bucket: str,
    strongest_excerpt: str,
    observations: list[dict[str, Any]],
    competitor: str,
    audience: str,
    channel: str,
    explicit_claim: str | None = None,
) -> str:
    competitor = normalize_competitor_for_copy(competitor, strongest_excerpt=strongest_excerpt, explicit_claim=explicit_claim)
    audience_phrase = normalize_task_audience(audience)
    ch = _clip_task_copy(channel, 100)
    signal_body = ""
    if observations:
        signal_body = sanitize_signal_summary_for_copy(str(observations[0].get("summary") or "").strip())
    if not signal_body:
        signal_body = (explicit_claim or strongest_excerpt or "").strip()
    signal_body = _clip_task_copy(signal_body, 420)
    stype = ""
    if observations:
        stype = str(observations[0].get("signal_type") or "").strip()
    type_tail = f" · observation_type={stype}" if stype else ""
    return (
        f"Signal (your workspace): {signal_body}{type_tail} · "
        f"competitor={_clip_task_copy(competitor, 100)} · channel={ch} · "
        f"audience={_clip_task_copy(audience_phrase, 80)} · move={move_bucket}"
    )


def synthesize_task_title(
    *,
    move_bucket: str,
    competitor: str,
    audience: str,
    channel: str,
    timing_window: str,
    strongest_excerpt: str,
    offer: str | None = None,
    explicit_asset: str | None = None,
    explicit_section: str | None = None,
    explicit_claim: str | None = None,
) -> str:
    competitor = normalize_competitor_for_copy(competitor, strongest_excerpt=strongest_excerpt, explicit_claim=explicit_claim)
    audience_phrase = normalize_task_audience(audience)
    tw = _clip_task_copy(timing_window, 48) or "this week"
    ch = _clip_task_copy(channel, 100)
    focus = _organic_task_focus(
        strongest_excerpt=strongest_excerpt,
        explicit_claim=explicit_claim,
        offer=offer,
        explicit_asset=explicit_asset,
        explicit_section=explicit_section,
    )
    if not focus:
        focus = _clip_task_copy(strongest_excerpt or channel or competitor, 220)
    return _clip_task_copy(
        " · ".join(
            [
                f"move={move_bucket}",
                f"channel={ch}",
                f"window={tw}",
                f"evidence={focus}",
                f"competitor={_clip_task_copy(competitor, 90)}",
                f"audience={_clip_task_copy(audience_phrase, 60)}",
            ]
        ),
        320,
    )


def synthesize_task_expected_advantage(
    *,
    move_bucket: str,
    competitor: str,
    audience: str,
    channel: str,
    timing_window: str,
    explicit_claim: str | None = None,
) -> str:
    competitor = normalize_competitor_for_copy(competitor, explicit_claim=explicit_claim)
    audience_phrase = normalize_task_audience(audience)
    ch = _clip_task_copy(channel, 100)
    tw = _clip_task_copy(timing_window, 48) or "this week"
    hint = _clip_task_copy(explicit_claim, 200)
    base = (
        f"Conversion and positioning for {_clip_task_copy(audience_phrase, 80)} {tw} tie to how you execute in {ch} "
        f"vs {_clip_task_copy(competitor, 100)} (move={move_bucket})"
    )
    if hint:
        base += f"; user evidence: {hint}"
    return base


def normalize_task_audience(audience: str) -> str:
    normalized = audience.strip()
    replacements = {
        "comparison-stage buyers": "buyers already comparing options",
        "comparison-stage buyer": "a buyer already comparing options",
        "buyers": "buyers",
    }
    return replacements.get(normalized, normalized)


def infer_competitor_claim(text: str) -> str | None:
    lowered = text.lower()
    if "free trial" in lowered:
        return "free trial"
    if "no engineering required" in lowered:
        return "no engineering required message"
    if "onboarding" in lowered:
        return "onboarding promise"
    if "pricing" in lowered:
        return "pricing comparison"
    if "testimonial" in lowered or "proof" in lowered:
        return "proof claim"
    return None


def fallback_competitor_reference(*, strongest_excerpt: str, explicit_claim: str | None = None) -> str:
    claim = explicit_claim or infer_competitor_claim(strongest_excerpt)
    if claim:
        return f"the competitor using {claim}"
    if "pricing" in strongest_excerpt.lower() or "onboarding" in strongest_excerpt.lower():
        return "the competitor setting the pricing expectation"
    return "the visible competitor"


def infer_title_asset(
    *,
    move_bucket: str,
    channel: str,
    strongest_excerpt: str,
    explicit_asset: str | None = None,
    explicit_section: str | None = None,
) -> str:
    return infer_task_asset(
        move_bucket=move_bucket,
        channel=channel,
        mechanism="",
        strongest_excerpt=strongest_excerpt,
        explicit_asset=explicit_asset,
        explicit_section=explicit_section,
    )


def infer_task_asset(
    *,
    move_bucket: str,
    channel: str,
    mechanism: str,
    strongest_excerpt: str,
    explicit_asset: str | None = None,
    explicit_section: str | None = None,
) -> str:
    def clean_phrase(value: str | None) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip(" .:-")).strip()

    ea = clean_phrase(explicit_asset)
    es = clean_phrase(explicit_section)
    ch = clean_phrase(channel)
    ex = clean_phrase(strongest_excerpt)
    mech = clean_phrase(mechanism)
    if ea and es:
        return _clip_task_copy(f"{ea} · {es} · {ch}", 220)
    if ea:
        return _clip_task_copy(f"{ea} · {ch}", 220) if ch else _clip_task_copy(ea, 220)
    if ex:
        return _clip_task_copy(ex, 200)
    if ch:
        return ch
    return _clip_task_copy(mech, 160) or move_bucket.replace("_", " ")


def build_task_execution_steps(
    *,
    move_bucket: str,
    source_refs: list[str],
    channel: str,
    audience: str,
    competitor: str,
    mechanism: str,
    strongest_excerpt: str,
    explicit_asset: str | None = None,
    explicit_section: str | None = None,
    explicit_claim: str | None = None,
) -> list[str]:
    source_summary = ", ".join(source_refs[:5]) if source_refs else "(no source refs)"
    asset = infer_task_asset(
        move_bucket=move_bucket,
        channel=channel,
        mechanism=mechanism,
        strongest_excerpt=strongest_excerpt,
        explicit_asset=explicit_asset,
        explicit_section=explicit_section,
    )
    claim_phrase = _organic_task_focus(
        strongest_excerpt=strongest_excerpt,
        explicit_claim=explicit_claim,
        explicit_asset=explicit_asset,
        explicit_section=explicit_section,
    ) or _clip_task_copy(strongest_excerpt, 320)
    mech_c = _clip_task_copy(mechanism, 360)
    return [
        _clip_task_copy(f"sources: {source_summary}", 420),
        _clip_task_copy(f"evidence: {claim_phrase}", 420),
        _clip_task_copy(f"channel: {channel} · audience: {audience} · competitor: {competitor} · move: {move_bucket}", 420),
        _clip_task_copy(f"surface_hint: {asset} · excerpt_or_notes: {mech_c}", 420),
    ]


def synthesize_done_definition(
    *,
    move_bucket: str,
    competitor: str,
    channel: str,
    audience: str,
    mechanism: str,
    strongest_excerpt: str,
    explicit_asset: str | None = None,
    explicit_section: str | None = None,
) -> str:
    asset = infer_task_asset(
        move_bucket=move_bucket,
        channel=channel,
        mechanism=mechanism,
        strongest_excerpt=strongest_excerpt,
        explicit_asset=explicit_asset,
        explicit_section=explicit_section,
    )
    ex = _clip_task_copy(strongest_excerpt, 260)
    return _clip_task_copy(
        f"Done: shipped in {channel} for {audience} · surface {asset} · "
        f"grounded in your excerpt: {ex} · competitor context {competitor} · {move_bucket}",
        420,
    )


def filter_clauses(clauses: list[str], tokens: tuple[str, ...]) -> list[str]:
    """Match tokens with word boundaries / offer-trial rules (avoids 'trial' ⊂ 'testimonial', 'offer' ⊂ 'offered')."""
    matched: list[str] = []
    for clause in clauses:
        if is_technical_residue(clause):
            continue
        normalized = " ".join(clause.lower().split())
        if any(clause_matches_keyword(normalized, token) for token in tokens):
            matched.append(clause)
    return matched


def source_refs_for_items(items: list[str], source_rows: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for item in items:
        lowered = item.lower()
        for row in source_rows:
            if lowered[:60] in row["raw_text"].lower():
                refs.append(row["source_ref"])
                break
    return unique_values(refs)


def unique_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def derive_topic_items(text: str) -> list[str]:
    normalized = text.lower()
    items: list[str] = []
    if any(token in normalized for token in ("seo", "search", "ranking")):
        items.append("Search and SEO language appears repeatedly across the ingested source set.")
    if any(token in normalized for token in ("marketing", "campaign", "demand generation")):
        items.append("Marketing or campaign positioning is part of the current market context.")
    if any(token in normalized for token in ("ai", "automation", "intelligence")):
        items.append("AI or intelligence claims are central to the current narrative.")
    if any(token in normalized for token in ("pricing", "package", "plan", "subscription")):
        items.append("Commercial packaging language is present and should be reviewed for buyer pressure.")
    if _commercial_offer_tokens_in_text(normalized):
        items.append("Offer-led conversion pressure is visible in the current source material.")
    return items


def is_technical_residue(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    if normalized in {"pdf", "metadata", "catalog", "version", "pages", "type"}:
        return True
    if normalized.startswith(("pdf ", "metadata ", "catalog ", "version ", "pages ", "type ")):
        return True
    tokens = set(normalized.replace(":", " ").split())
    residue_tokens = {"pdf", "metadata", "catalog", "version", "pages", "type", "xref", "obj", "root", "parent"}
    return bool(tokens) and tokens.issubset(residue_tokens)


def run_observation_loop(config: WorkerBridgeConfig) -> None:
    queue_dir = Path(config.queue_dir)
    while True:
        processed = 0
        for path in sorted(queue_dir.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as handle:
                    payload = json.load(handle)
                source = SourcePackage(**payload)
                sync_observations_for_source(source, config)
                path.unlink(missing_ok=True)
                processed += 1
            except Exception:  # noqa: BLE001
                update_monitor_state(
                    "continuous_observation_loop",
                    "error",
                    last_source_ref=path.stem,
                    details={"queue_file": str(path)},
                    path=config.local_db_path,
                )
                continue
        update_monitor_state(
            "continuous_observation_loop",
            "idle" if processed == 0 else "processed",
            details={"processed_count": processed},
            path=config.local_db_path,
        )
        time.sleep(config.poll_interval_seconds)


def serve() -> None:
    from agent_chappie.worker_logging import configure_worker_logging

    configure_worker_logging()
    config = load_config()
    observer = threading.Thread(target=run_observation_loop, args=(config,), daemon=True)
    observer.start()
    server = create_server(config)
    server.serve_forever()

if __name__ == "__main__":
    serve()
