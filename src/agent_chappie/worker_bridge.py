from __future__ import annotations

import json
import os
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
    list_draft_segments,
    list_evidence_units,
    list_generation_memory_rows,
    list_task_feedback_rows,
    list_observations_for_source,
    list_managed_jobs,
    list_managed_sources,
    list_monitor_rows,
    list_recent_observations,
    list_recent_source_snapshots,
    replace_draft_segments,
    replace_evidence_units,
    save_source_snapshot,
    save_generation_memory_rows,
    save_replacement_history,
    save_task_feedback_rows,
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
    evidence_units = build_evidence_units(source_package.project_id, refreshed_sources, aggregated or observations, fact_chips)
    replace_evidence_units(source_package.project_id, evidence_units, path=config.local_db_path)
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
    feedback_rows = list_task_feedback_rows(source_package.project_id, path=config.local_db_path)
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
            if repaired_payload is not None:
                result_document["result_payload"] = repaired_payload
                job_result = validate_job_result(result_document)
            else:
                fallback_payload = generate_guaranteed_task_triplet(
                    source_package,
                    aggregated or observations,
                    draft_segments,
                    feedback_rows,
                    generation_memory_rows,
                )
                result_document["result_payload"] = fallback_payload
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

    if resource == "task-feedback" and method == "POST" and len(parts) == 3:
        return process_task_feedback(project_id, payload, config), HTTPStatus.OK

    if resource == "checklist" and method == "POST" and len(parts) == 3:
        job_id = str(payload.get("job_id") or f"regenerated_{project_id}_{int(time.time() * 1000)}")
        app_id = str(payload.get("app_id") or "consultant_followup_web")
        result_document = regenerate_project_checklist(project_id, config, job_id=job_id, app_id=app_id)
        return {"job_result": result_document, "workspace": build_workspace_payload(project_id, config)}, HTTPStatus.OK

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
    competitor_lc = competitor.lower()
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
    monitor_rows = list_monitor_rows(path=config.local_db_path)
    fact_chips = build_fact_chips(source_rows, observation_rows, knowledge_rows)
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


def process_task_feedback(project_id: str, payload: dict[str, Any], config: WorkerBridgeConfig) -> dict[str, Any]:
    job_id = str(payload.get("job_id") or "")
    feedback_items = payload.get("task_feedback_items") or []
    if not job_id or not isinstance(feedback_items, list) or not feedback_items:
        raise ValueError("Task feedback requires a job id and at least one feedback item.")

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
            }
        )
    save_task_feedback_rows(project_id, job_id, rows, path=config.local_db_path)
    save_generation_memory_rows(project_id, build_generation_memory_rows(rows), path=config.local_db_path)

    result_document = regenerate_project_checklist(
        project_id,
        config,
        job_id=job_id,
        app_id="consultant_followup_web",
        confidence=0.74,
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
    return {"job_result": result_document, "workspace": build_workspace_payload(project_id, config)}


def regenerate_project_checklist(
    project_id: str,
    config: WorkerBridgeConfig,
    *,
    job_id: str,
    app_id: str,
    confidence: float = 0.78,
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
    result_payload = generate_learning_checklist(
        seed_source,
        observation_rows,
        draft_segments,
        knowledge_cards,
        fact_chips,
        evidence_units,
        feedback_rows,
        generation_memory_rows,
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
            [
                "Compare your current positioning against the strongest pattern in the source set.",
                "Add one denser source if the market story still feels incomplete.",
            ],
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
            "The source set points to the competitors most likely shaping the current comparison set.",
            "These names should anchor who you benchmark, monitor, and position against first.",
            [
                "Verify whether the top named competitor is truly in your comparison set.",
                "Add one competitor-specific source if the detected list feels too thin.",
            ],
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
            "Packaging and onboarding language are the strongest commercial signals currently visible in the source set.",
            "If these signals keep appearing, your offer may need a clearer pricing or packaging response before buyers compare options.",
            [
                "Check whether your current package framing is weaker than the source set suggests.",
                "Prepare one pricing-page adjustment if a competitor pattern keeps repeating.",
            ],
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
            "We can see which offer, proof, and positioning angles competitors are using to shape buyer expectations right now.",
            "If you do not answer the strongest angle in the right channel, your offer can lose urgency during live comparisons.",
            [
                "Draft one response angle that answers the strongest positioning claim.",
                "Check whether your enrollment or landing-page copy reflects the same buyer pressure.",
            ],
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
            "The source set contains proof language that may shape trust and buyer confidence.",
            "If competitors are using stronger proof than you are, they can win comparison-stage buyers even without a better product.",
            [
                "Review whether your best proof matches the strongest proof signal in the market.",
                "Add a stronger proof source if the current evidence is still weak.",
            ],
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
        open_questions.append("Region is still weakly inferred. Add one source with explicit geography or local market scope.")
    if not competitor_items:
        open_questions.append("No clear named competitors were extracted. A denser market source would improve competitor confidence.")
    if source_rows and not any(
        unit["unit_kind"] in {"pricing", "pricing_change", "offer", "proof", "positioning", "messaging_shift", "proof_signal"}
        for unit in all_units
    ):
        open_questions.append("We still do not have enough commercial pressure evidence to support a stronger action move.")
    open_questions.extend(missing_evidence_categories(all_units)[:2])
    if not open_questions:
        open_questions.append("No major confidence gaps are currently blocking the knowledge surface.")
    cards.append(
        knowledge_card(
            "open_questions",
            "Open Questions",
            "Weak-confidence areas and unresolved questions the operator may want to confirm or correct.",
            open_questions,
            "The system still has unresolved areas that could change recommendation quality.",
            "Correcting these gaps will improve future task precision and reduce weak inference.",
            [
                "Confirm or edit the cards above if any inference is wrong.",
                "Add one source that resolves the highest-confidence gap first.",
            ],
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
    audience = infer_operator_audience(domain, detail)
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
    has_proof_signal = any(token in lowered for token in ("proof", "testimonial", "integration", "trust"))
    has_offer_signal = any(token in lowered for token in ("trial", "offer", "discount", "positioning", "message"))

    if segment["segment_kind"] in {"pricing", "pricing_packaging"} or any(token in lowered for token in ("price", "pricing", "package", "bundle", "onboarding")):
        competitor_name = competitor or fallback_competitor_reference(
            strongest_excerpt=strongest_excerpt,
            explicit_claim=explicit_claim,
        )
        comparison_channel = explicit_channel or comparison_channel
        mechanism = "Add a side-by-side pricing comparison and onboarding FAQ that lowers perceived adoption friction."
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
        mechanism = "Add concrete proof blocks where hesitant buyers compare trust and implementation confidence."
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
    if segment["segment_kind"] in {"offer", "offer_positioning", "positioning"} or any(token in lowered for token in ("trial", "offer", "discount", "positioning", "message")):
        competitor_name = competitor or fallback_competitor_reference(
            strongest_excerpt=strongest_excerpt,
            explicit_claim=explicit_claim,
        )
        offer = detail.get("offer") or strongest_offer_hint(segment_text)
        channel = explicit_channel or primary_channel
        mechanism = "Replace the exposed claim in the live page copy with a direct response to the strongest competitor angle."
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
        why_now = synthesize_task_why_now(
            move_bucket="information_request",
            strongest_excerpt=strongest_excerpt,
            observations=bundle_observations,
            competitor=competitor or fallback_competitor_reference(
                strongest_excerpt=strongest_excerpt,
                explicit_claim=explicit_claim,
            ),
            audience=audience,
            channel="same workspace",
            explicit_claim=explicit_claim,
        )
        return {
            "rank": 0,
            "title": title,
            "why_now": why_now,
            "expected_advantage": "Improves conversion and win rate this week by resolving the missing competitor, pricing, or buyer-pressure fact that is limiting the next best action.",
            "evidence_refs": evidence_refs,
            "task_type": "information_request",
            "move_bucket": "information_request",
            "target_segment": audience,
            "execution_steps": build_task_execution_steps(
                move_bucket="information_request",
                source_refs=supporting_source_refs,
                channel="same workspace",
                audience=audience,
                competitor=competitor or fallback_competitor_reference(
                    strongest_excerpt=strongest_excerpt,
                    explicit_claim=explicit_claim,
                ),
                mechanism="Request one missing proprietary fact in a single message and add it back to this workspace.",
                strongest_excerpt=strongest_excerpt,
                explicit_asset=explicit_asset,
                explicit_section=explicit_section,
                explicit_claim=explicit_claim,
            ),
            "done_definition": synthesize_done_definition(
                move_bucket="information_request",
                competitor=competitor or fallback_competitor_reference(
                    strongest_excerpt=strongest_excerpt,
                    explicit_claim=explicit_claim,
                ),
                channel="same workspace",
                audience=audience,
                mechanism="Request one missing proprietary fact in a single message and add it back to this workspace.",
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
        mechanism = "Secure direct access before another operator captures the transition window."
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
        mechanism = "Add concrete proof blocks where hesitant buyers compare trust signals."
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
    audience = "buyers" if domain == "general" else "families"
    audience_phrase = normalize_task_audience(audience)
    strongest_competitor = normalize_competitor_fact(source.competitor or "") or fallback_competitor_reference(
        strongest_excerpt=source.raw_text,
        explicit_claim=None,
    )

    for segment in strongest:
        evidence_refs = segment.get("evidence_refs") or [f"segment::{segment['segment_id']}"]
        lowered_segment = str(segment["segment_text"]).lower()
        if segment["segment_kind"] == "competitor":
            candidates.append(
                {
                    "rank": 0,
                    "title": "Capture one live competitor pricing, proof, and offer page this week so we can replace guesswork with the exact claims buyers will compare against you",
                    "why_now": f"We identified a competitor signal that is still too broad for a stronger move: {segment['segment_text']}",
                    "expected_advantage": f"Improves conversion for active {audience} this week by replacing broad market assumptions with the exact competitor claims now shaping comparison decisions.",
                    "evidence_refs": evidence_refs,
                    "task_type": "information_request",
                    "move_bucket": "information_request",
                }
            )
        elif segment["segment_kind"] == "proof" or any(token in lowered_segment for token in ("proof", "testimonial", "integration", "trust")):
            candidates.append(
                {
                    "rank": 0,
                    "title": f"Add two proof blocks this week on the {infer_proof_channel(domain, lowered_segment)} where {audience_phrase} hesitate most",
                    "why_now": f"We found a proof signal in the market: {segment['segment_text']}",
                    "expected_advantage": f"Improves conversion for {audience_phrase} this week by reducing trust friction versus the strongest proof language currently visible in the market.",
                    "evidence_refs": evidence_refs,
                    "task_type": "general_business_value",
                    "move_bucket": "proof_or_trust_move",
                }
            )
        elif segment["segment_kind"] in {"pricing", "pricing_packaging"} or any(token in lowered_segment for token in ("pricing", "price", "package", "bundle", "onboarding")):
            candidates.append(
                {
                    "rank": 0,
                    "title": f"Ship one simpler pricing or onboarding entry move this week on the {infer_primary_channel(domain, lowered_segment)} before {audience_phrase} decide your offer is harder to adopt",
                    "why_now": f"We found commercial friction in the market picture: {segment['segment_text']}",
                    "expected_advantage": f"Improves conversion for active {audience} this week by lowering adoption friction before buyers choose a lower-friction competitor path.",
                    "evidence_refs": evidence_refs,
                    "task_type": "direct_competitive_move",
                    "move_bucket": "pricing_or_offer_move",
                }
            )
        elif segment["segment_kind"] in {"offer", "offer_positioning", "positioning"} or any(token in lowered_segment for token in ("trial", "offer", "positioning", "message", "homepage", "hero", "comparison")):
            candidates.append(
                {
                    "rank": 0,
                    "title": f"Rewrite the strongest homepage or comparison claim this week before {strongest_competitor} shapes how {audience_phrase} judge your offer",
                    "why_now": f"We found a visible claim in the market picture: {segment['segment_text']}",
                    "expected_advantage": f"Improves shortlist conversion for active {audience_phrase} this week by replacing a live competitor claim before it becomes the default comparison language.",
                    "evidence_refs": evidence_refs,
                    "task_type": "tactical_response",
                    "move_bucket": "messaging_or_positioning_move",
                }
            )
        elif segment["segment_kind"] == "source_clause":
            candidates.append(
                {
                    "rank": 0,
                    "title": f"Turn the strongest validated clause into a live {infer_primary_channel(domain, lowered_segment)} response this week instead of leaving it as passive context",
                    "why_now": f"We isolated a high-importance market signal in this source that is still sitting below task threshold: {segment['segment_text']}",
                    "expected_advantage": "Improves conversion and execution speed this week by converting one validated market observation into a concrete business move before the window closes.",
                    "evidence_refs": evidence_refs,
                    "task_type": "general_business_value",
                    "move_bucket": "messaging_or_positioning_move",
                }
            )

    info_request_count = sum(1 for candidate in candidates if candidate.get("task_type") == "information_request")

    if not candidates:
        candidates.append(
            {
                "rank": 0,
                    "title": "Request one sharper source this week that exposes a competitor move, buyer objection, or timing window we can act on",
                "why_now": "The drafter created knowledge segments, but the writer still lacks one decisive competitor or timing signal to turn that market picture into a dominant move.",
                "expected_advantage": "Improves win rate and conversion next week by filling the evidence gap that is currently preventing a stronger competitive response.",
                "evidence_refs": [f"segment::{segment['segment_id']}" for segment in strongest[:2]] or [source.source_ref],
                "task_type": "information_request",
                "move_bucket": "information_request",
            }
        )
    elif not has_actionable_candidates and info_request_count == 0:
        candidates.append(
            {
                "rank": 0,
                "title": "Request one sharper source this week that exposes the missing competitor move or buyer objection behind this market pattern",
                "why_now": "We can see market pressure, but one decisive source is still missing before we can recommend a stronger intercept or capture move.",
                "expected_advantage": "Improves task quality this week by adding the exact missing evidence needed to convert market context into a stronger business move.",
                "evidence_refs": [f"segment::{segment['segment_id']}" for segment in strongest[:2]] or [source.source_ref],
                "task_type": "information_request",
                "move_bucket": "information_request",
            }
        )

    if has_actionable_candidates and len(candidates) < 3:
        anchor_segment = strongest[0] if strongest else None
        anchor_text = (anchor_segment["segment_text"] if anchor_segment else source.raw_text).lower()
        channel = infer_primary_channel(domain, anchor_text)
        fallback_actions = [
            {
                "rank": 0,
                "title": f"Add one trust-building proof block on the {infer_proof_channel(domain, anchor_text)} this week before {strongest_competitor} hardens buyer expectations",
                "why_now": (
                    f"We already have enough visible pressure to act, but your proof surface is still weaker than the live comparison pressure: {anchor_segment['segment_text']}"
                    if anchor_segment
                    else "We already have enough visible pressure to act, but your proof surface is still weaker than the live comparison pressure."
                ),
                "expected_advantage": f"Improves conversion for active {audience_phrase} this week by making trust visible before {strongest_competitor} becomes the safer default.",
                "evidence_refs": [f"segment::{segment['segment_id']}" for segment in strongest[:2]] or [source.source_ref],
                "task_type": "exploratory_action",
                "move_bucket": "proof_or_trust_move",
            },
            {
                "rank": 0,
                "title": f"Rewrite one comparison-facing claim on the {channel} this week before {strongest_competitor} shapes how {audience_phrase} frame the decision",
                "why_now": (
                    f"We already have enough visible pressure to act, but one cleaner claim response is still missing: {anchor_segment['segment_text']}"
                    if anchor_segment
                    else "We already have enough visible pressure to act, but one cleaner claim response is still missing from the current checklist."
                ),
                "expected_advantage": f"Improves shortlist conversion for active {audience_phrase} this week by giving buyers a clearer decision frame before {strongest_competitor} owns it.",
                "evidence_refs": [f"segment::{segment['segment_id']}" for segment in strongest[:2]] or [source.source_ref],
                "task_type": "exploratory_action",
                "move_bucket": "messaging_or_positioning_move",
            },
        ]
        existing_buckets = {str(candidate.get("move_bucket") or "") for candidate in candidates}
        for fallback_action in fallback_actions:
            if len(candidates) >= 3:
                break
            if str(fallback_action["move_bucket"]) in existing_buckets:
                continue
            candidates.append(fallback_action)
            existing_buckets.add(str(fallback_action["move_bucket"]))

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
        judged.insert(
            0,
            {
                "rank": 0,
                "title": adjusted_text,
                "why_now": f"You previously corrected a similar task after we surfaced this signal change: {row.get('original_title')}. We are carrying that correction forward as the stronger replacement.",
                "expected_advantage": str(row.get("original_expected_advantage") or "Improves conversion and execution speed this week by using the operator-corrected action instead of repeating a weaker task template."),
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
        for index in range(len(final_tasks), 3):
            fallback_title = (
                f"Add one trust-building proof block this week before {fallback_competitor} hardens buyer expectations"
                if index == 2
                else f"Ship one specific response move this week in the strongest visible channel before {fallback_competitor} hardens buyer expectations"
            )
            normalized_title = normalize_task_key(fallback_title)
            if normalized_title in fallback_titles:
                fallback_title = f"Add one specific proof or pricing block this week before {fallback_competitor} hardens buyer expectations"
                normalized_title = normalize_task_key(fallback_title)
            fallback_titles.add(normalized_title)
            final_tasks.append(
                {
                    "rank": 0,
                    "title": fallback_title,
                    "why_now": "We still need one more concrete signal-backed move to keep the checklist at three actions this week.",
                    "expected_advantage": "Improves conversion and execution speed this week by keeping the checklist active while a stronger replacement is still forming.",
                    "evidence_refs": [source.source_ref],
                    "task_type": "exploratory_action",
                    "move_bucket": "proof_or_trust_move" if index == 2 else "messaging_or_positioning_move",
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
    if strongest:
        for segment in strongest:
            fallback_tasks.append(
                {
                    "rank": 0,
                    "title": f"Request one sharper source this week that resolves the strongest {humanize_fact_category(str(segment['segment_kind']).replace('open_questions', 'market'))} gap before the next buyer decision window",
                    "why_now": f"We only have partial evidence from this source set, and the strongest drafted segment is still below the confident-action threshold: {segment['segment_text']}",
                    "expected_advantage": "Improves conversion and task quality this week by turning a partial market picture into an evidence-backed move before the next decision window closes.",
                    "evidence_refs": segment.get("evidence_refs") or [f"segment::{segment['segment_id']}"],
                    "task_type": "exploratory_action",
                    "move_bucket": "information_request",
                }
            )
    while len(fallback_tasks) < 3:
        fallback_tasks.append(
            {
                "rank": 0,
                "title": "Pull one more competitor proof, pricing, or offer source this week and force the next checklist toward a stronger move",
                "why_now": "The current evidence is still too thin for a stronger action, so the checklist is using exploratory pressure instead of going silent.",
                "expected_advantage": "Improves conversion and win rate next week by replacing missing evidence with one concrete competitor signal we can act on.",
                "evidence_refs": [source.source_ref],
                "task_type": "exploratory_action",
                "move_bucket": "information_request",
            }
        )
    judged = judge_tasks(fallback_tasks[:6], source, feedback_rows, generation_memory_rows)
    return {
        "recommended_tasks": judged[:3],
        "summary": "Three exploratory or moderate actions were emitted because the product policy forbids an empty checklist.",
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

    if candidate_payloads:
        candidate_payloads.sort(
            key=lambda item: (task_payload_specificity_score(item[1]), 1 if item[0] == "segment" else 0),
            reverse=True,
        )
        return candidate_payloads[0][1]

    return generate_guaranteed_task_triplet(
        source_package,
        observations,
        draft_segments,
        feedback_rows,
        generation_memory_rows,
    )


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
    title = task["title"].lower()
    why = task["why_now"].lower()
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
    if any(token in title or token in why for token in ("before", "closure", "capture", "pricing", "trial", "offer")):
        score += 3
    score += generation_memory_adjustment(task, generation_memory_rows or [])
    return score


def generation_memory_adjustment(task: dict[str, Any], generation_memory_rows: list[dict[str, Any]]) -> int:
    if not generation_memory_rows:
        return 0

    normalized_title = normalize_task_key(task.get("title", ""))
    bucket = task_move_bucket(task)
    channel = infer_primary_channel("academy" if "enrollment" in task.get("title", "").lower() else "general", task.get("title", "").lower())
    adjustment = 0
    for row in generation_memory_rows:
        kind = str(row.get("memory_kind") or "")
        pattern_key = str(row.get("pattern_key") or "")
        signal_value = str(row.get("signal_value") or "")
        weight = int(round(float(row.get("weight") or 0)))
        if kind == "avoid_title" and pattern_key == normalized_title:
            adjustment -= max(3, weight)
        elif kind == "avoid_phrase" and signal_value and signal_value in task.get("title", "").lower():
            adjustment -= max(2, weight)
        elif kind == "avoid_bucket" and pattern_key == bucket:
            adjustment -= max(1, weight)
        elif kind == "prefer_channel" and signal_value and signal_value == channel:
            adjustment += max(2, weight)
        elif kind == "prefer_phrase" and signal_value and signal_value in task.get("title", "").lower():
            adjustment += max(2, weight)
    return adjustment


def build_generation_memory_rows(feedback_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in feedback_rows:
        feedback_id = str(row.get("feedback_id") or "")
        feedback_type = str(row.get("feedback_type") or "")
        original_title = str(row.get("original_title") or "")
        normalized_title = normalize_task_key(original_title)
        title_lower = original_title.lower()
        comment = str(row.get("feedback_comment") or "").strip().lower()
        adjusted_text = str(row.get("adjusted_text") or "").strip()

        if feedback_type in {"declined", "commented", "deleted_with_annotation", "held_for_later"} and normalized_title:
            rows.append(
                {
                    "memory_kind": "avoid_title",
                    "pattern_key": normalized_title,
                    "signal_value": original_title,
                    "weight": 3.0 if feedback_type in {"declined", "deleted_with_annotation"} else 2.0 if feedback_type == "commented" else 1.0,
                    "source_feedback_id": feedback_id,
                }
            )
        if any(token in comment for token in ("generic", "vague", "broad", "weak", "fuzzy")):
            for phrase in ("buyer-facing response", "operator response", "sharper source", "request one sharper source"):
                if phrase in title_lower:
                    rows.append(
                        {
                            "memory_kind": "avoid_phrase",
                            "pattern_key": normalize_task_key(original_title),
                            "signal_value": phrase,
                            "weight": 2.0,
                            "source_feedback_id": feedback_id,
                        }
                    )
        if any(token in comment for token in ("overlap", "duplicate", "same", "similar")):
            rows.append(
                {
                    "memory_kind": "avoid_bucket",
                    "pattern_key": task_move_bucket({"title": original_title, "why_now": "", "task_type": ""}),
                    "signal_value": original_title,
                    "weight": 1.0,
                    "source_feedback_id": feedback_id,
                }
            )
        if adjusted_text:
            adjusted_lower = adjusted_text.lower()
            rows.append(
                {
                    "memory_kind": "prefer_phrase",
                    "pattern_key": normalize_task_key(adjusted_text),
                    "signal_value": adjusted_lower,
                    "weight": 2.0,
                    "source_feedback_id": feedback_id,
                }
            )
            preferred_channel = infer_primary_channel("academy" if "enrollment" in adjusted_lower else "general", adjusted_lower)
            rows.append(
                {
                    "memory_kind": "prefer_channel",
                    "pattern_key": task_move_bucket({"title": adjusted_text, "why_now": "", "task_type": ""}),
                    "signal_value": preferred_channel,
                    "weight": 1.0,
                    "source_feedback_id": feedback_id,
                }
            )
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
    if any(token in text for token in ("pricing", "price", "offer", "trial", "discount", "onboarding")):
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


def normalize_task_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


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
        if cleaned:
            return cleaned
    return None


def infer_operator_audience(domain: str, detail: dict[str, str | None]) -> str:
    tier = detail.get("tier")
    if domain == "academy" and tier:
        return f"{tier} families"
    if domain == "academy":
        return "families"
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
    if any(token in normalized for token in ("academy", "club", "u14", "families", "intake", "enrollment")):
        return "academy"
    return "general"


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
        ("pricing", ("price", "pricing", "fee", "plan", "package", "packaging", "bundle", "subscription", "onboarding")),
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
    if any(token in all_text.lower() for token in ("trial", "discount", "offer", "voucher", "scholarship")):
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
        if "trial" in normalized.lower():
            return "Trial-based acquisition pressure is visible in the source set."
        if any(token in normalized.lower() for token in ("discount", "voucher", "scholarship")):
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
    return cleaned


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
    competitor = next((unit["competitor"] for unit in evidence_units if clean_entity(str(unit.get("competitor") or ""))), None)
    if not competitor:
        competitor = next((row["competitor"] for row in knowledge_rows if clean_entity(row["competitor"])), "Comparison set still forming")
    pricing_observation = next((row for row in observation_rows if row["signal_type"] == "pricing_change"), None)
    offer_observation = next((row for row in observation_rows if row["signal_type"] == "offer"), None)
    closure_observation = next((row for row in observation_rows if row["signal_type"] == "closure"), None)
    asset_sale_observation = next((row for row in observation_rows if row["signal_type"] == "asset_sale"), None)
    pricing_units = [unit for unit in evidence_units if unit["unit_kind"] in {"pricing", "pricing_change"}]
    offer_units = [unit for unit in evidence_units if unit["unit_kind"] in {"offer", "positioning", "messaging_shift"}]
    proof_units = [unit for unit in evidence_units if unit["unit_kind"] in {"proof", "proof_signal"}]
    pricing_clusters = cluster_units_by_action_shape(pricing_units)
    offer_clusters = cluster_units_by_action_shape(offer_units)
    proof_clusters = cluster_units_by_action_shape(proof_units)
    top_pricing_cluster = pick_best_action_cluster(pricing_units)
    top_offer_cluster = pick_best_action_cluster(offer_units)
    top_proof_cluster = pick_best_action_cluster(proof_units)

    pricing_position = "No pricing pressure detected yet."
    if pricing_observation:
        pricing_position = (
            f"{pricing_observation['competitor']} is resetting buyer price expectations in "
            f"{humanize_region(pricing_observation['region'])}, which exposes any weaker entry offer you still show."
        )
    elif top_pricing_cluster:
        pricing_position = summarize_snapshot_cluster_pressure(
            cluster=top_pricing_cluster,
            fallback_competitor=competitor,
            fallback="Pricing pressure is visible in the comparison set.",
        )

    acquisition_strategy = "No competitor is clearly winning on low-friction acquisition yet."
    if offer_observation:
        acquisition_strategy = (
            f"{offer_observation['competitor']} is lowering switching friction in "
            f"{humanize_region(offer_observation['region'])} through offer-led acquisition."
        )
    elif asset_sale_observation:
        acquisition_strategy = (
            f"{asset_sale_observation['competitor']} is creating a cost-side acquisition opening through asset pressure."
        )
    elif top_offer_cluster:
        acquisition_strategy = summarize_snapshot_cluster_pressure(
            cluster=top_offer_cluster,
            fallback_competitor=competitor,
            fallback="Offer or positioning pressure is shaping low-friction acquisition.",
        )

    active_threats = [summarize_observation_threat(row) for row in observation_rows[:3]] or ["No immediate competitive threats are strongly evidenced yet."]
    cluster_threats = build_snapshot_cluster_threats(pricing_clusters, offer_clusters, proof_clusters, competitor)
    if cluster_threats:
        active_threats = unique_values(cluster_threats + active_threats)[:3]
    immediate_opportunities = []
    if closure_observation:
        immediate_opportunities.append(
            f"Move first on {closure_observation['competitor']} before the closure pressure turns into someone else's acquisition gain."
        )
    if offer_observation and pricing_observation:
        immediate_opportunities.append(
            f"Answer both {offer_observation['competitor']}'s offer pressure and {pricing_observation['competitor']}'s pricing move with one visible comparison response."
        )
    open_questions_card = next((card for card in knowledge_cards if card["knowledge_id"] == "open_questions"), None)
    if open_questions_card and len(immediate_opportunities) < 3:
        immediate_opportunities.extend(open_questions_card["potential_moves"][: 3 - len(immediate_opportunities)])
    if not immediate_opportunities:
        immediate_opportunities.append("Add one more source to sharpen the next recommendation cycle.")

    current_weakness = "No dominant weakness is strongly evidenced yet."
    if offer_observation:
        current_weakness = "Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition."
    elif pricing_observation:
        current_weakness = "Weakness: your current price framing may look exposed if you do not answer the new comparison anchor quickly."
    elif top_proof_cluster:
        current_weakness = summarize_snapshot_weakness(top_proof_cluster, competitor)

    risk_level = "low"
    if closure_observation or (pricing_observation and offer_observation):
        risk_level = "high"
    elif pricing_observation or offer_observation or asset_sale_observation:
        risk_level = "medium"

    return {
        "pricing_position": pricing_position,
        "acquisition_strategy_comparison": acquisition_strategy,
        "current_weakness": current_weakness,
        "active_threats": active_threats,
        "immediate_opportunities": immediate_opportunities[:3],
        "reference_competitor": competitor,
        "risk_level": risk_level,
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


def summarize_snapshot_cluster_pressure(cluster: dict[str, Any], fallback_competitor: str, fallback: str) -> str:
    competitor = str(cluster.get("competitor") or fallback_competitor or "A competitor").strip()
    asset = str(cluster.get("asset") or "").strip()
    channel = str(cluster.get("channel") or "").strip()
    claim = str(cluster.get("claim") or "").strip()
    excerpt = str(cluster.get("excerpt") or "").strip()
    if asset and channel and claim:
        return f"{competitor} is using {asset} in the {channel} to push the {claim} claim into live buyer comparisons."
    if excerpt and claim:
        return f"{competitor} is pushing the {claim} claim into live comparisons: {excerpt[:180]}"
    if asset and channel:
        return f"{competitor} is making the {channel} more competitive through {asset}."
    if excerpt:
        return f"{competitor} is shaping live comparisons through this visible pressure: {excerpt[:180]}"
    if claim:
        return f"{competitor} is pushing the {claim} claim into the active comparison set."
    return fallback


def build_snapshot_cluster_threats(
    pricing_clusters: list[dict[str, Any]],
    offer_clusters: list[dict[str, Any]],
    proof_clusters: list[dict[str, Any]],
    fallback_competitor: str,
) -> list[str]:
    threats: list[str] = []
    for cluster in (pricing_clusters[:1] + offer_clusters[:1] + proof_clusters[:1]):
        summary = summarize_snapshot_cluster_pressure(
            cluster=cluster,
            fallback_competitor=fallback_competitor,
            fallback="Competitive pressure is active.",
        )
        if summary and summary not in threats:
            threats.append(summary)
    return threats[:3]


def summarize_snapshot_weakness(cluster: dict[str, Any], fallback_competitor: str) -> str:
    competitor = str(cluster.get("competitor") or fallback_competitor or "a competitor").strip()
    asset = str(cluster.get("asset") or "proof").strip()
    channel = str(cluster.get("channel") or "the current comparison path").strip()
    claim = str(cluster.get("claim") or "trust").strip()
    return f"Weakness: your current {asset} in the {channel} may look weaker if you do not answer {competitor}'s {claim} claim quickly."


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


def summarize_observation_threat(observation: dict[str, Any]) -> str:
    competitor = observation.get("competitor") or "A competitor"
    region = humanize_region(observation.get("region", "region_unknown"))
    signal_type = observation.get("signal_type")
    if signal_type == "pricing_change":
        return f"{competitor} is changing pricing pressure in {region}."
    if signal_type == "offer":
        return f"{competitor} is using a direct offer to win buyers in {region}."
    if signal_type == "closure":
        return f"{competitor} is unstable in {region}, creating a fast-moving capture opportunity."
    if signal_type == "asset_sale":
        return f"{competitor} is creating a low-cost asset opportunity in {region}."
    return observation.get("summary", "A competitive change is active.")


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
        "insight": feedback_original_payload.get("insight", insight) if isinstance(feedback_original_payload, dict) else insight,
        "implication": feedback.get("corrected_implication") if feedback and feedback.get("corrected_implication") else implication,
        "potential_moves": feedback.get("corrected_potential_moves") if feedback and feedback.get("corrected_potential_moves") else potential_moves,
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


def strongest_unit_excerpt(units: list[dict[str, Any]]) -> str | None:
    if not units:
        return None
    strongest = max(units, key=lambda unit: float(unit.get("confidence") or 0))
    excerpt = str(strongest.get("excerpt") or "").strip()
    return excerpt[:220] if excerpt else None


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
        return "We have only a thin market picture so far, so the strongest pattern is still forming."
    top = market_units[0]
    competitor = top.get("competitor") or "the visible comparison set"
    return f"We can already see the market leaning on {humanize_fact_category(str(top.get('unit_kind') or 'market')).lower()} pressure, with {competitor} helping set buyer expectations."


def market_summary_implication(market_units: list[dict[str, Any]]) -> str:
    if not market_units:
        return "Add one denser source if you want the next recommendation cycle to rely on something stronger than broad context."
    top = market_units[0]
    category = str(top.get("unit_kind") or "market")
    if category in {"pricing", "pricing_change"}:
        return "If you do not answer the current pricing and onboarding comparison directly, buyers can adopt the competitor's lower-friction frame before you respond."
    if category in {"offer", "positioning", "messaging_shift"}:
        return "If you do not answer the strongest buyer-facing claim in the right channel, your offer can lose urgency during live comparisons."
    if category in {"proof", "proof_signal"}:
        return "If you do not strengthen your visible proof, comparison-stage buyers can trust the stronger story first."
    return "This pattern is strong enough to change how buyers compare options, so it should influence the next visible move."


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
    competitor = str(cluster.get("competitor") or "The market").strip()
    asset = str(cluster.get("asset") or "").strip()
    channel = str(cluster.get("channel") or "").strip()
    claim = str(cluster.get("claim") or "").strip()
    unit_kind = str(cluster.get("unit_kind") or "market")
    if asset and channel and claim:
        return f"{competitor} is pushing {claim} pressure through {asset} on the {channel}."
    if asset and channel:
        return f"{competitor} is changing expectations through {asset} on the {channel}."
    if claim:
        return f"{competitor} is reinforcing {claim} as a live comparison claim."
    return f"{competitor} is contributing to {humanize_fact_category(unit_kind).lower()} pressure in the active market."


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
    return strongest_unit_excerpt(matched)


def missing_evidence_categories(units: list[dict[str, Any]]) -> list[str]:
    categories = {str(unit.get("unit_kind") or "") for unit in units}
    gaps: list[str] = []
    if not categories.intersection({"pricing", "pricing_change"}):
        gaps.append("We still need stronger pricing evidence before we can recommend a tighter commercial response.")
    if not categories.intersection({"offer", "positioning", "messaging_shift"}):
        gaps.append("We still need a clearer buyer-facing offer or positioning signal before we can sharpen the response channel.")
    if not categories.intersection({"proof", "proof_signal"}):
        gaps.append("We still need stronger trust or proof evidence before we can recommend the right proof move with confidence.")
    return gaps


def strongest_offer_hint(text: str) -> str | None:
    lowered = text.lower()
    if "trial" in lowered:
        return "trial"
    if "discount" in lowered:
        return "discount"
    if "testimonial" in lowered or "proof" in lowered:
        return "proof"
    if "integration" in lowered:
        return "integration"
    return None


def infer_task_move_bucket(segment_kind: str, lowered_text: str) -> str:
    if segment_kind in {"pricing", "pricing_packaging"} or any(token in lowered_text for token in ("price", "pricing", "package", "bundle", "onboarding")):
        return "pricing_or_offer_move"
    if segment_kind in {"proof"} or any(token in lowered_text for token in ("proof", "testimonial", "integration", "trust")):
        return "proof_or_trust_move"
    if segment_kind in {"offer", "offer_positioning", "positioning"} or any(token in lowered_text for token in ("trial", "offer", "discount", "positioning", "message")):
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
    audience_phrase = normalize_task_audience(audience)
    claim_phrase = explicit_claim or strongest_excerpt.strip()
    if observations:
        primary = observations[0]
        summary = str(primary.get("summary") or strongest_excerpt).strip()
        signal_type = str(primary.get("signal_type") or "signal").replace("_", " ")
        return f"We detected a {signal_type} signal in your sources tied to {competitor}: {summary} If you do not answer that specific pressure in the {channel}, {audience_phrase} can keep comparing you through {competitor}'s claim."

    if move_bucket == "pricing_or_offer_move":
        return f"We detected pricing or onboarding pressure tied to {competitor}: {claim_phrase} If you do not answer it in the {channel}, {audience_phrase} can adopt {competitor}'s lower-friction commercial expectation first."
    if move_bucket == "messaging_or_positioning_move":
        return f"We detected a visible comparison signal tied to {competitor}: {claim_phrase} If you do not answer it in the {channel}, {audience_phrase} can default to that framing."
    if move_bucket == "intercept_or_capture_move":
        return f"We detected a closure, asset, or transition signal tied to {competitor}: {claim_phrase} This creates a short-lived opening that should be acted on through {channel}."
    if move_bucket == "proof_or_trust_move":
        return f"We detected proof or trust pressure tied to {competitor}: {claim_phrase} This is already influencing how hesitant {audience_phrase} judge credibility."
    return f"We detected a concrete signal in your sources: {claim_phrase} This is the strongest reason to act now."


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
    audience_phrase = normalize_task_audience(audience)
    competitor_claim = explicit_claim or offer or infer_competitor_claim(strongest_excerpt) or "its strongest visible claim"
    competitor_phrase = competitor_possessive_phrase(competitor)
    title_asset = infer_title_asset(
        move_bucket=move_bucket,
        channel=channel,
        strongest_excerpt=strongest_excerpt,
        explicit_asset=explicit_asset,
        explicit_section=explicit_section,
    )
    if move_bucket == "pricing_or_offer_move":
        return f"Add {title_asset} {timing_window} before {competitor_phrase} {competitor_claim} sets expectations for {audience_phrase}"
    if move_bucket == "messaging_or_positioning_move":
        return f"Rewrite {title_asset} {timing_window} to answer {competitor_phrase} {competitor_claim} before {audience_phrase} default to it"
    if move_bucket == "intercept_or_capture_move":
        return f"Contact {competitor} {timing_window} and secure first access to customers, staff, assets, or distribution before the window closes"
    if move_bucket == "proof_or_trust_move":
        prefix = "Add" if title_asset.startswith("proof") else "Add proof blocks to"
        return f"{prefix} {title_asset} {timing_window} so hesitant {audience_phrase} do not trust {competitor} first"
    if move_bucket == "information_request":
        if any(token in strongest_excerpt.lower() for token in ("pricing", "onboarding", "offer", "proof")):
            return f"Request the missing proprietary pricing, offer, or buyer-proof fact {timing_window} before making the wrong response move"
        return f"Request the missing competitor or timing fact {timing_window} before making the wrong response move"
    return f"Ship the strongest visible response in {title_asset} {timing_window} before {competitor} gains more ground"


def synthesize_task_expected_advantage(
    *,
    move_bucket: str,
    competitor: str,
    audience: str,
    channel: str,
    timing_window: str,
    explicit_claim: str | None = None,
) -> str:
    audience_phrase = normalize_task_audience(audience)
    claim_phrase = explicit_claim or "its strongest visible claim"
    if move_bucket == "pricing_or_offer_move":
        return f"Increases conversion for active {audience_phrase} {timing_window} by answering {competitor}'s {claim_phrase} in the {channel}."
    if move_bucket == "messaging_or_positioning_move":
        return f"Increases shortlist conversion for {audience_phrase} {timing_window} by replacing {competitor}'s {claim_phrase} with a stronger response in the {channel}."
    if move_bucket == "intercept_or_capture_move":
        return f"Creates near-term revenue or cost advantage {timing_window} by moving through {channel} before {competitor}'s transition window closes."
    if move_bucket == "proof_or_trust_move":
        return f"Increases conversion and win rate for hesitant {audience_phrase} {timing_window} by strengthening trust signals in the {channel} before {competitor} hardens its {claim_phrase}."
    return f"Improves conversion and execution speed {timing_window} by making a stronger move in the {channel} before {competitor} gains more ground."


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


def competitor_possessive_phrase(competitor: str) -> str:
    cleaned = competitor.strip()
    if cleaned.lower().startswith("the competitor ") or cleaned.lower().startswith("the visible competitor"):
        return cleaned
    if cleaned.endswith("s"):
        return f"{cleaned}'"
    return f"{cleaned}'s"


def infer_title_asset(
    *,
    move_bucket: str,
    channel: str,
    strongest_excerpt: str,
    explicit_asset: str | None = None,
    explicit_section: str | None = None,
) -> str:
    asset = infer_task_asset(
        move_bucket=move_bucket,
        channel=channel,
        mechanism="",
        strongest_excerpt=strongest_excerpt,
        explicit_asset=explicit_asset,
        explicit_section=explicit_section,
    )
    asset = asset.replace(" on the ", " on ").replace(" in the ", " in ")
    asset = asset.replace("proof block in proof section", "proof block")
    asset = asset.replace("proof blocks in proof section", "proof blocks")
    return asset


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

    def compose_asset_phrase(asset_text: str, section_text: str, channel_text: str) -> str:
        asset_norm = clean_phrase(asset_text)
        section_norm = clean_phrase(section_text)
        channel_norm = clean_phrase(channel_text)
        asset_tokens = {token for token in re.findall(r"[a-z0-9]+", asset_norm.lower()) if len(token) >= 4}
        section_tokens = {token for token in re.findall(r"[a-z0-9]+", section_norm.lower()) if len(token) >= 4}
        if section_norm and section_norm.lower() in asset_norm.lower():
            section_norm = ""
        if asset_tokens and section_tokens and len(asset_tokens & section_tokens) >= 1:
            section_norm = ""
        if channel_norm and channel_norm.lower() in asset_norm.lower():
            channel_norm = ""
        if channel_norm == "homepage comparison section" and ("hero" in asset_norm.lower() or "homepage" in asset_norm.lower()):
            channel_norm = "homepage"
        phrase = asset_norm
        if section_norm:
            phrase = f"{phrase} in the {section_norm}"
        if channel_norm:
            phrase = f"{phrase} on the {channel_norm}"
        return phrase

    def asset_matches_bucket(asset_text: str, bucket: str) -> bool:
        lowered = asset_text.lower()
        if bucket == "pricing_or_offer_move":
            return not any(token in lowered for token in ("proof block", "proof blocks", "testimonial"))
        if bucket == "proof_or_trust_move":
            return any(token in lowered for token in ("proof", "testimonial", "trust"))
        if bucket == "messaging_or_positioning_move":
            return not any(token in lowered for token in ("pricing comparison block and onboarding faq",))
        return True

    if explicit_asset and asset_matches_bucket(explicit_asset, move_bucket):
        return compose_asset_phrase(explicit_asset, explicit_section or "", channel)
    excerpt = strongest_excerpt.lower()
    if move_bucket == "pricing_or_offer_move":
        if "faq" in excerpt or "onboarding" in excerpt:
            return f"pricing comparison block and onboarding FAQ on the {channel}"
        return f"pricing comparison block on the {channel}"
    if move_bucket == "messaging_or_positioning_move":
        if "hero" in channel.lower():
            return f"hero section copy on the {channel}"
        if "homepage" in channel.lower():
            return "homepage comparison copy"
        return f"comparison section copy on the {channel}"
    if move_bucket == "proof_or_trust_move":
        return f"proof blocks on the {channel}"
    if move_bucket == "intercept_or_capture_move":
        return "direct outreach message and follow-up ask"
    if move_bucket == "information_request":
        return "single missing proprietary fact"
    return mechanism.lower().replace(".", "")


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
    source_summary = ", ".join(source_refs[:3]) if source_refs else "the linked source set"
    asset = infer_task_asset(
        move_bucket=move_bucket,
        channel=channel,
        mechanism=mechanism,
        strongest_excerpt=strongest_excerpt,
        explicit_asset=explicit_asset,
        explicit_section=explicit_section,
    )
    claim_phrase = explicit_claim or strongest_excerpt
    if move_bucket == "pricing_or_offer_move":
        return [
            f"Pull the exact pricing, onboarding, and proof claims from {source_summary}, especially the claim behind this excerpt: {claim_phrase}",
            f"Turn those claims into a live {asset} using this mechanism: {mechanism}.",
            f"Publish the updated {asset} this week so active {audience} see it in the {channel}.",
            f"Send the updated {asset} into live comparisons and check whether {competitor}-style pricing or onboarding objections drop.",
        ]
    if move_bucket == "messaging_or_positioning_move":
        return [
            f"Pull the strongest live claim from {source_summary}, especially the angle {competitor} is using against {audience}: {claim_phrase}",
            f"Rewrite the {asset} using this mechanism: {mechanism}.",
            f"Publish the updated {asset} this week in the first comparison section buyers will see.",
            f"Check whether the updated {asset} now answers the objection or offer pressure tied to {competitor}.",
        ]
    if move_bucket == "proof_or_trust_move":
        return [
            f"Pull the strongest trust and proof patterns from {source_summary}, especially what makes {competitor} more credible to {audience}: {claim_phrase}",
            f"Add the planned {asset} using this mechanism: {mechanism}.",
            f"Publish the {asset} this week where hesitant buyers see it first on the {channel}.",
            f"Check whether trust objections drop when {audience} compare you against {competitor}.",
        ]
    if move_bucket == "intercept_or_capture_move":
        return [
            f"Pull the exact transition, closure, or asset evidence from {source_summary}, anchored to this excerpt: {claim_phrase}",
            f"Contact {competitor} using this mechanism: {mechanism}.",
            "Secure the next meeting, inventory list, or first-right-of-access this week before another operator moves.",
            f"Check whether the opportunity with {competitor} is now advancing on your terms instead of staying theoretical.",
        ]
    if move_bucket == "information_request":
        return [
            f"Review {source_summary} and isolate the one missing proprietary fact we still cannot collect automatically from this evidence: {claim_phrase}",
            "Request that specific missing input in one message, not a broad research ask.",
            "Add the new evidence back into this same workspace this week so the checklist can regenerate from it.",
            "Check that the next regeneration replaces the exploratory task with a stronger action move.",
        ]
    return [
        f"Use the strongest evidence from {source_summary}, especially {claim_phrase}, to define the exact asset or channel change required against {competitor}.",
        f"Create the exact {asset} using this mechanism: {mechanism}.",
        f"Publish the change in the {channel} this week so {audience} can actually experience the move.",
        f"Check whether the result reduced the threat from {competitor} or captured the opportunity described in the expected impact.",
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
    if move_bucket == "pricing_or_offer_move":
        return f"The live {asset} explicitly answers {competitor}'s pricing or onboarding claim and is visible to active {audience}."
    if move_bucket == "messaging_or_positioning_move":
        return f"The live {asset} answers {competitor}'s strongest buyer-facing claim in the first comparison section."
    if move_bucket == "proof_or_trust_move":
        return f"The live {asset} contains at least two concrete proof elements that answer the trust pressure behind this task."
    if move_bucket == "intercept_or_capture_move":
        return f"You have a confirmed reply, meeting, or first-right-of-access from {competitor} tied to the exposed opportunity."
    if move_bucket == "information_request":
        return "The missing proprietary fact is added to this workspace and the checklist regenerates from it."
    return f"The live {asset} is visible in the {channel} and directly answers the evidence behind this task."


def filter_clauses(clauses: list[str], tokens: tuple[str, ...]) -> list[str]:
    return [
        clause
        for clause in clauses
        if not is_technical_residue(clause) and any(token in clause.lower() for token in tokens)
    ]


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
    config = load_config()
    observer = threading.Thread(target=run_observation_loop, args=(config,), daemon=True)
    observer.start()
    server = create_server(config)
    server.serve_forever()
