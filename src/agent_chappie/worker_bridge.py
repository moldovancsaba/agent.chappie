from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agent_chappie.local_store import (
    create_managed_job,
    create_managed_source,
    delete_source_snapshot,
    delete_managed_job,
    delete_managed_source,
    fetch_knowledge_feedback_rows,
    fetch_knowledge_rows,
    get_source_snapshot,
    initialize_local_store,
    insert_observations,
    list_observations_for_source,
    list_managed_jobs,
    list_managed_sources,
    list_monitor_rows,
    list_recent_observations,
    list_recent_source_snapshots,
    save_source_snapshot,
    update_managed_job,
    update_managed_source,
    update_monitor_state,
    update_source_snapshot,
    upsert_knowledge_feedback,
    upsert_knowledge_state,
)
from agent_chappie.observation_engine import (
    SourcePackage,
    build_source_hash,
    clean_entity,
    deduplicate_observations,
    extract_clauses,
    extract_named_entities,
    extract_observations,
    generate_recommended_tasks,
    normalize_source_package,
    recover_source_context,
    repair_recommended_tasks,
    utc_now_iso,
)
from agent_chappie.validation import ValidationError, validate_job_request, validate_job_result


@dataclass
class WorkerBridgeConfig:
    host: str = "127.0.0.1"
    port: int = 8787
    shared_secret: str = "change-me"
    queue_dir: str = "runtime_status/observation_queue"
    local_db_path: str = "runtime_status/agent_brain.sqlite3"
    poll_interval_seconds: int = 60


def load_config() -> WorkerBridgeConfig:
    return WorkerBridgeConfig(
        host=os.environ.get("AGENT_WORKER_HOST", "127.0.0.1"),
        port=int(os.environ.get("AGENT_WORKER_PORT", "8787")),
        shared_secret=os.environ.get("AGENT_SHARED_SECRET", "change-me"),
        queue_dir=os.environ.get("AGENT_OBSERVATION_QUEUE_DIR", "runtime_status/observation_queue"),
        local_db_path=os.environ.get("AGENT_LOCAL_DB_PATH", "runtime_status/agent_brain.sqlite3"),
        poll_interval_seconds=int(os.environ.get("AGENT_OBSERVATION_POLL_SECONDS", "60")),
    )


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
    aggregated = list_recent_observations(source_package.project_id, path=config.local_db_path)
    result_payload = generate_recommended_tasks(source_package, aggregated or observations)
    knowledge_cards = build_knowledge_cards(
        list_recent_source_snapshots(source_package.project_id, path=config.local_db_path),
        aggregated or observations,
        fetch_knowledge_rows(source_package.project_id, path=config.local_db_path),
        fetch_knowledge_feedback_rows(source_package.project_id, path=config.local_db_path),
    )
    used_source_refs: set[str] = set()

    if "recommended_tasks" in result_payload:
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
            if repaired_payload is None:
                job_result = validate_job_result(
                    {
                        "job_id": job_request["job_id"],
                        "app_id": job_request["app_id"],
                        "project_id": job_request["project_id"],
                        "status": "blocked",
                        "completed_at": utc_now_iso(),
                        "result_payload": {
                            "reason": "insufficient_output_quality",
                        },
                    }
                )
            else:
                result_document["result_payload"] = repaired_payload
                job_result = validate_job_result(result_document)
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
    else:
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

    processing_summary = (
        job_result["result_payload"].get("summary")
        if job_result["status"] == "complete" and isinstance(job_result["result_payload"], dict)
        else "Knowledge extracted; no strong checklist action yet."
        if knowledge_cards
        else job_result["result_payload"].get("reason", "Source processed")
    )
    update_source_snapshot(
        source_package.source_ref,
        {
            "status": "processed" if job_result["status"] == "complete" else "blocked",
            "processing_summary": processing_summary,
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
    parts = path.strip("/").split("/")
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
            corrected_title=payload.get("corrected_title"),
            corrected_summary=payload.get("corrected_summary"),
            corrected_items=payload.get("corrected_items"),
            path=config.local_db_path,
        )
        return build_workspace_payload(project_id, config), HTTPStatus.OK

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


def build_workspace_payload(project_id: str, config: WorkerBridgeConfig) -> dict[str, Any]:
    source_rows = list_recent_source_snapshots(project_id, path=config.local_db_path)
    observation_rows = list_recent_observations(project_id, path=config.local_db_path)
    knowledge_rows = fetch_knowledge_rows(project_id, path=config.local_db_path)
    knowledge_feedback_rows = fetch_knowledge_feedback_rows(project_id, path=config.local_db_path)
    monitor_rows = list_monitor_rows(path=config.local_db_path)
    knowledge_cards = build_knowledge_cards(source_rows, observation_rows, knowledge_rows, knowledge_feedback_rows)
    source_cards = build_ingested_source_cards(source_rows, observation_rows, knowledge_cards)

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
    knowledge_cards = build_knowledge_cards(
        list_recent_source_snapshots(project_id, path=config.local_db_path),
        list_recent_observations(project_id, path=config.local_db_path),
        fetch_knowledge_rows(project_id, path=config.local_db_path),
        fetch_knowledge_feedback_rows(project_id, path=config.local_db_path),
    )
    update_source_snapshot(
        source_ref,
        {
            "status": "processed",
            "processing_summary": f"Processed {len(observations)} signals and {len(knowledge_cards)} knowledge cards",
            "signal_count": len(list_observations_for_source(project_id, source_ref, path=config.local_db_path)),
            "knowledge_count": sum(1 for card in knowledge_cards if source_ref in card["source_refs"]),
        },
        path=config.local_db_path,
    )


def build_ingested_source_cards(
    source_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
    knowledge_cards: list[dict[str, Any]],
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
                "signal_count": signal_count,
                "knowledge_count": knowledge_count,
                "last_used_in_checklist": bool(row.get("last_used_in_checklist")),
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
) -> list[dict[str, Any]]:
    feedback_lookup = {row["knowledge_id"]: row for row in feedback_rows}
    clauses = unique_clauses(source_rows)
    entities = unique_entities(source_rows, observation_rows, knowledge_rows)
    cards: list[dict[str, Any]] = []

    market_items = []
    if source_rows:
        market_items.append(f"{len(source_rows)} ingested source{'s' if len(source_rows) != 1 else ''} are shaping the current knowledge state.")
    if observation_rows:
        market_items.append(f"{sum(1 for row in observation_rows if row['signal_type'] == 'pricing_change')} pricing signal(s) are active.")
        market_items.append(f"{sum(1 for row in observation_rows if row['signal_type'] in {'offer', 'asset_sale'})} offer or asset signal(s) are active.")
    topic_items = derive_topic_items(" ".join(row["raw_text"] for row in source_rows))
    market_items.extend(topic_items[:3])
    cards.append(
        knowledge_card(
            "market_summary",
            "Market Summary",
            "What the system currently knows about this market or project from the ingested sources.",
            market_items or ["No market synthesis has been derived yet."],
            observation_rows[:4],
            [row["source_ref"] for row in source_rows[:4]],
            0.78 if source_rows else 0.22,
            feedback_lookup,
        )
    )

    cards.append(
        knowledge_card(
            "competitors_detected",
            "Competitors Detected",
            "Named companies, schools, clubs, or products the worker has extracted from the source set.",
            entities[:6] or ["No named competitors have been extracted with enough confidence yet."],
            observation_rows[:4],
            [row["source_ref"] for row in source_rows[:4]],
            0.74 if entities else 0.28,
            feedback_lookup,
        )
    )

    pricing_items = filter_clauses(
        clauses,
        ("price", "pricing", "fee", "plan", "package", "packaging", "bundle", "subscription", "onboarding"),
    )
    cards.append(
        knowledge_card(
            "pricing_packaging",
            "Pricing / Packaging",
            "Commercial packaging and pricing observations the worker has extracted from the source material.",
            pricing_items[:5] or ["No pricing or packaging observations are strong enough yet."],
            [row for row in observation_rows if row["signal_type"] == "pricing_change"][:4],
            source_refs_for_items(pricing_items[:5], source_rows),
            0.71 if pricing_items else 0.24,
            feedback_lookup,
        )
    )

    positioning_items = filter_clauses(
        clauses,
        ("offer", "trial", "discount", "voucher", "no engineering", "no-code", "speed", "faster", "implementation", "position"),
    )
    cards.append(
        knowledge_card(
            "offer_positioning",
            "Offer / Positioning",
            "Offer language, positioning claims, and tactical market signals found in the sources.",
            positioning_items[:5] or ["No clear positioning or offer observations have been extracted yet."],
            [row for row in observation_rows if row["signal_type"] in {"offer", "messaging_shift"}][:4],
            source_refs_for_items(positioning_items[:5], source_rows),
            0.73 if positioning_items else 0.25,
            feedback_lookup,
        )
    )

    proof_items = filter_clauses(clauses, ("testimonial", "logo", "proof", "case study", "integration", "customer"))
    cards.append(
        knowledge_card(
            "proof_signals",
            "Proof Signals",
            "Trust cues, proof points, and credibility patterns extracted from the current source set.",
            proof_items[:5] or ["No proof signals have been extracted yet."],
            [row for row in observation_rows if row["signal_type"] == "proof_signal"][:4],
            source_refs_for_items(proof_items[:5], source_rows),
            0.69 if proof_items else 0.21,
            feedback_lookup,
        )
    )

    open_questions = []
    if not any(row.get("region") and row["region"] != "region_unknown" for row in source_rows + knowledge_rows):
        open_questions.append("Region is still weakly inferred. Add one source with explicit geography or local market scope.")
    if not entities:
        open_questions.append("No clear named competitors were extracted. A denser market source would improve competitor confidence.")
    if source_rows and not observation_rows:
        open_questions.append("The source produced knowledge but not enough action-quality signals yet. Checklist can stay blocked while Know More stays populated.")
    if not open_questions:
        open_questions.append("No major confidence gaps are currently blocking the knowledge surface.")
    cards.append(
        knowledge_card(
            "open_questions",
            "Open Questions",
            "Weak-confidence areas and unresolved questions the operator may want to confirm or correct.",
            open_questions,
            observation_rows[:2],
            [row["source_ref"] for row in source_rows[:3]],
            0.55,
            feedback_lookup,
        )
    )

    return cards


def knowledge_card(
    knowledge_id: str,
    title: str,
    summary: str,
    items: list[str],
    evidence_rows: list[dict[str, Any]],
    source_refs: list[str],
    confidence: float,
    feedback_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    feedback = feedback_lookup.get(knowledge_id)
    return {
        "knowledge_id": knowledge_id,
        "title": feedback.get("corrected_title") if feedback and feedback.get("corrected_title") else title,
        "summary": feedback.get("corrected_summary") if feedback and feedback.get("corrected_summary") else summary,
        "items": feedback.get("corrected_items") if feedback and feedback.get("corrected_items") else items,
        "source_refs": unique_values(source_refs),
        "evidence_refs": unique_values([row["signal_id"] for row in evidence_rows]),
        "confidence": round(confidence, 2),
        "annotation_status": feedback["status"] if feedback else "pending",
    }


def unique_clauses(source_rows: list[dict[str, Any]]) -> list[str]:
    clauses: list[str] = []
    seen: set[str] = set()
    for row in source_rows:
        for clause in extract_clauses(row["raw_text"]):
            normalized = clause.strip()
            if len(normalized) < 16:
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


def filter_clauses(clauses: list[str], tokens: tuple[str, ...]) -> list[str]:
    return [clause for clause in clauses if any(token in clause.lower() for token in tokens)]


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
    if any(token in normalized for token in ("trial", "discount", "offer")):
        items.append("Offer-led conversion pressure is visible in the current source material.")
    return items


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
    config = load_config()
    observer = threading.Thread(target=run_observation_loop, args=(config,), daemon=True)
    observer.start()
    server = create_server(config)
    server.serve_forever()
