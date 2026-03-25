from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any


def local_db_path() -> str:
    return os.environ.get("AGENT_LOCAL_DB_PATH", "runtime_status/agent_brain.sqlite3")


def initialize_local_store(path: str | None = None) -> str:
    db_path = path or local_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(
            """
            create table if not exists system_observations (
              signal_id text primary key,
              project_id text not null,
              competitor text not null,
              region text not null,
              signal_type text not null,
              summary text not null,
              source_ref text not null,
              observed_at text not null,
              confidence real not null,
              business_impact text not null,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              superseded_by text
            );

            create index if not exists idx_local_observations_project_region
              on system_observations(project_id, region, observed_at desc);
            create index if not exists idx_local_observations_competitor
              on system_observations(competitor, observed_at desc);
            create index if not exists idx_local_observations_signal_type
              on system_observations(signal_type, observed_at desc);

            create table if not exists source_snapshots (
              source_ref text primary key,
              project_id text not null,
              source_kind text not null,
              project_summary text not null,
              raw_text text not null,
              competitor text,
              region text,
              source_hash text not null,
              display_label text,
              status text not null default 'processed',
              processing_summary text,
              key_takeaway text,
              business_impact text,
              linked_task_titles_json text,
              source_confidence real,
              signal_count integer not null default 0,
              knowledge_count integer not null default 0,
              last_used_in_checklist integer not null default 0,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists project_knowledge_state (
              project_id text not null,
              region text not null,
              competitor text not null,
              latest_observed_at text not null,
              knowledge_json text not null,
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              primary key (project_id, region, competitor)
            );

            create table if not exists monitor_state (
              job_name text primary key,
              last_run_at text,
              last_source_ref text,
              status text not null,
              details_json text,
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists managed_sources (
              source_id text primary key,
              project_id text not null,
              label text not null,
              source_kind text not null,
              content_text text not null,
              repeat_interval text not null default 'never',
              repeat_anchor_at text,
              status text not null,
              last_run_at text,
              last_result_status text,
              last_result_summary text,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists managed_jobs (
              managed_job_id text primary key,
              project_id text not null,
              name text not null,
              trigger_type text not null,
              schedule_text text,
              status text not null,
              source_id text,
              last_run_at text,
              last_result_status text,
              last_action_summary text,
              last_expected_impact text,
              last_runs_json text,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists knowledge_feedback (
              knowledge_id text not null,
              project_id text not null,
              status text not null,
              confidence_source text,
              original_payload_json text,
              corrected_title text,
              corrected_summary text,
              corrected_implication text,
              corrected_potential_moves_json text,
              corrected_items_json text,
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              primary key (knowledge_id, project_id)
            );

            create table if not exists draft_knowledge_segments (
              segment_id text primary key,
              project_id text not null,
              segment_kind text not null,
              title text not null,
              segment_text text not null,
              source_refs_json text not null,
              evidence_refs_json text not null,
              importance real not null,
              confidence real not null,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists draft_segment_feedback (
              segment_id text not null,
              project_id text not null,
              status text not null,
              reason text,
              original_payload_json text,
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              primary key (segment_id, project_id)
            );

            create table if not exists task_feedback (
              feedback_id text primary key,
              task_id text,
              job_id text not null,
              project_id text not null,
              original_title text not null,
              original_expected_advantage text,
              feedback_type text not null,
              feedback_comment text,
              adjusted_text text,
              replacement_generated integer not null default 0,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists replacement_history (
              replacement_id text primary key,
              project_id text not null,
              prior_task_title text not null,
              replacement_title text not null,
              source_feedback_id text,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists generation_memory (
              memory_id text primary key,
              project_id text not null,
              memory_kind text not null,
              pattern_key text not null,
              signal_value text,
              weight real not null default 1.0,
              source_feedback_id text,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists project_active_checklist (
              project_id text primary key,
              job_id text not null,
              tasks_json text not null,
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists evidence_units (
              unit_id text primary key,
              project_id text not null,
              source_ref text not null,
              unit_kind text not null,
              label text not null,
              excerpt text,
              competitor text,
              segment text,
              channel text,
              section text,
              asset text,
              claim text,
              timing text,
              confidence real not null,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create table if not exists atomic_facts (
              fact_id text primary key,
              project_id text not null,
              source_ref text not null,
              fact_type text not null,
              fact_key text not null,
              fact_value_json text not null,
              clause_text text,
              trace_ref text,
              confidence real not null,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create index if not exists idx_atomic_facts_project_type
              on atomic_facts(project_id, fact_type, created_at desc);

            create table if not exists intelligence_cards (
              card_id text primary key,
              project_id text not null,
              insight text not null,
              implication text not null,
              potential_moves_json text not null,
              segment text,
              competitor text,
              channel text,
              fact_refs_json text not null,
              source_refs_json text not null,
              state text not null default 'candidate',
              expires_at text,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create index if not exists idx_intelligence_cards_project_state
              on intelligence_cards(project_id, state, updated_at desc);

            create table if not exists card_scores (
              card_id text primary key references intelligence_cards(card_id) on delete cascade,
              project_id text not null,
              confidence real not null,
              impact_score real not null,
              freshness_score real not null,
              evidence_strength real not null,
              rank_score real not null,
              scored_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create index if not exists idx_card_scores_project_rank
              on card_scores(project_id, rank_score desc, confidence desc);

            create table if not exists card_actions (
              action_id text primary key,
              card_id text not null references intelligence_cards(card_id) on delete cascade,
              project_id text not null,
              action_type text not null,
              note text,
              created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            create index if not exists idx_card_actions_project
              on card_actions(project_id, created_at desc);

            create table if not exists card_weight_profiles (
              project_id text primary key,
              w_confidence real not null default 0.45,
              w_impact real not null default 0.40,
              w_urgency real not null default 0.15,
              sample_count integer not null default 0,
              updated_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
            """
        )
        _ensure_column(connection, "source_snapshots", "display_label", "text")
        _ensure_column(connection, "source_snapshots", "status", "text not null default 'processed'")
        _ensure_column(connection, "source_snapshots", "processing_summary", "text")
        _ensure_column(connection, "source_snapshots", "key_takeaway", "text")
        _ensure_column(connection, "source_snapshots", "business_impact", "text")
        _ensure_column(connection, "source_snapshots", "linked_task_titles_json", "text")
        _ensure_column(connection, "source_snapshots", "source_confidence", "real")
        _ensure_column(connection, "source_snapshots", "signal_count", "integer not null default 0")
        _ensure_column(connection, "source_snapshots", "knowledge_count", "integer not null default 0")
        _ensure_column(connection, "source_snapshots", "last_used_in_checklist", "integer not null default 0")
        _ensure_column(connection, "managed_sources", "repeat_interval", "text not null default 'never'")
        _ensure_column(connection, "managed_sources", "repeat_anchor_at", "text")
        _ensure_column(connection, "knowledge_feedback", "confidence_source", "text")
        _ensure_column(connection, "knowledge_feedback", "original_payload_json", "text")
        _ensure_column(connection, "knowledge_feedback", "corrected_implication", "text")
        _ensure_column(connection, "knowledge_feedback", "corrected_potential_moves_json", "text")
        _ensure_column(connection, "evidence_units", "section", "text")
        _ensure_column(connection, "evidence_units", "asset", "text")
        _ensure_column(connection, "evidence_units", "claim", "text")
        _ensure_column(connection, "task_feedback", "action_type", "text")
        _ensure_column(connection, "card_scores", "quarantine_reason", "text")
        _ensure_column(connection, "card_scores", "gate_flags_json", "text")
        _ensure_flashcard_pipeline_runs_table(connection)
        _ensure_trinity_atom_progress_table(connection)
    finally:
        connection.close()
    return db_path


def _ensure_flashcard_pipeline_runs_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists flashcard_pipeline_runs (
          run_id text primary key,
          job_id text not null,
          project_id text not null,
          pipeline_source text not null,
          reason text,
          detail_json text,
          created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_flashcard_pipeline_runs_project
          on flashcard_pipeline_runs(project_id, created_at desc)
        """
    )


def _ensure_trinity_atom_progress_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists trinity_atom_progress (
          row_id text primary key,
          project_id text not null,
          job_id text not null,
          atom_index integer not null default -1,
          stage text not null,
          payload_json text not null,
          created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_trinity_progress_project
          on trinity_atom_progress(project_id, created_at desc)
        """
    )


@contextmanager
def _connect(path: str | None = None) -> Iterator[sqlite3.Connection]:
    db_path = initialize_local_store(path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    existing = {
        row[1]
        for row in connection.execute(f"pragma table_info({table_name})").fetchall()
    }
    if column_name not in existing:
        try:
            connection.execute(f"alter table {table_name} add column {column_name} {column_sql}")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise


def save_source_snapshot(source: dict[str, Any], source_hash: str, path: str | None = None) -> None:
    display_label = derive_source_display_label(source)
    with _connect(path) as connection:
        connection.execute(
            """
            insert into source_snapshots (
              source_ref,
              project_id,
              source_kind,
              project_summary,
              raw_text,
              competitor,
              region,
              source_hash,
              display_label,
              status
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(source_ref) do update set
              project_summary = excluded.project_summary,
              raw_text = excluded.raw_text,
              competitor = excluded.competitor,
              region = excluded.region,
              source_hash = excluded.source_hash,
              display_label = coalesce(source_snapshots.display_label, excluded.display_label),
              status = coalesce(source_snapshots.status, excluded.status)
            """,
            (
                source["source_ref"],
                source["project_id"],
                source["source_kind"],
                source["project_summary"],
                source["raw_text"],
                source.get("competitor"),
                source.get("region"),
                source_hash,
                display_label,
                "received",
            ),
        )


def derive_source_display_label(source: dict[str, Any]) -> str:
    if source.get("file_name"):
        return str(source["file_name"])
    raw_text = str(source.get("raw_text") or "").strip()
    first_clause = raw_text.splitlines()[0].split(".")[0].strip() if raw_text else ""
    if source.get("source_kind") == "manual_text" and first_clause:
        compact = " ".join(first_clause.split())
        return compact[:72] + ("..." if len(compact) > 72 else "")
    return str(source.get("source_ref") or "Source")


def insert_observations(project_id: str, observations: list[dict[str, Any]], path: str | None = None) -> None:
    if not observations:
        return
    with _connect(path) as connection:
        for observation in observations:
            connection.execute(
                """
                insert into system_observations (
                  signal_id,
                  project_id,
                  competitor,
                  region,
                  signal_type,
                  summary,
                  source_ref,
                  observed_at,
                  confidence,
                  business_impact,
                  superseded_by
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(signal_id) do update set
                  summary = excluded.summary,
                  observed_at = excluded.observed_at,
                  confidence = excluded.confidence,
                  business_impact = excluded.business_impact,
                  superseded_by = excluded.superseded_by
                """,
                (
                    observation["signal_id"],
                    project_id,
                    observation["competitor"],
                    observation["region"],
                    observation["signal_type"],
                    observation["summary"],
                    observation["source_ref"],
                    observation["observed_at"],
                    observation["confidence"],
                    observation["business_impact"],
                    observation.get("superseded_by"),
                ),
            )


def list_recent_observations(project_id: str, region: str | None = None, path: str | None = None) -> list[dict[str, Any]]:
    where = ["project_id = ?"]
    params: list[Any] = [project_id]
    if region:
        where.append("region = ?")
        params.append(region)
    where.append("superseded_by is null")
    query = f"""
        select
          signal_id,
          project_id,
          competitor,
          region,
          signal_type,
          summary,
          source_ref,
          observed_at,
          confidence,
          business_impact
        from system_observations
        where {' and '.join(where)}
        order by observed_at desc
        limit 200
    """
    with _connect(path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def upsert_knowledge_state(observations: list[dict[str, Any]], path: str | None = None) -> None:
    if not observations:
        return
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for observation in observations:
        key = (
            observation["project_id"],
            observation["region"],
            observation["competitor"],
        )
        bucket = grouped.setdefault(
            key,
            {
                "project_id": observation["project_id"],
                "region": observation["region"],
                "competitor": observation["competitor"],
                "latest_observed_at": observation["observed_at"],
                "signals": [],
            },
        )
        bucket["signals"].append(
            {
                "signal_id": observation["signal_id"],
                "signal_type": observation["signal_type"],
                "business_impact": observation["business_impact"],
                "summary": observation["summary"],
                "source_ref": observation["source_ref"],
            }
        )
        if observation["observed_at"] > bucket["latest_observed_at"]:
            bucket["latest_observed_at"] = observation["observed_at"]

    with _connect(path) as connection:
        for bucket in grouped.values():
            connection.execute(
                """
                insert into project_knowledge_state (
                  project_id,
                  region,
                  competitor,
                  latest_observed_at,
                  knowledge_json
                )
                values (?, ?, ?, ?, ?)
                on conflict(project_id, region, competitor) do update set
                  latest_observed_at = excluded.latest_observed_at,
                  knowledge_json = excluded.knowledge_json,
                  updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                """,
                (
                    bucket["project_id"],
                    bucket["region"],
                    bucket["competitor"],
                    bucket["latest_observed_at"],
                    json.dumps(bucket["signals"]),
                ),
            )


def update_monitor_state(
    job_name: str,
    status: str,
    last_source_ref: str | None = None,
    details: dict[str, Any] | None = None,
    path: str | None = None,
) -> None:
    with _connect(path) as connection:
        connection.execute(
            """
            insert into monitor_state (
              job_name,
              last_run_at,
              last_source_ref,
              status,
              details_json
            )
            values (
              ?,
              strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
              ?,
              ?,
              ?
            )
            on conflict(job_name) do update set
              last_run_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
              last_source_ref = excluded.last_source_ref,
              status = excluded.status,
              details_json = excluded.details_json,
              updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (
                job_name,
                last_source_ref,
                status,
                json.dumps(details or {}),
            ),
        )


def fetch_knowledge_rows(project_id: str, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select project_id, region, competitor, latest_observed_at, knowledge_json, updated_at
            from project_knowledge_state
            where project_id = ?
            order by latest_observed_at desc
            """,
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_recent_source_snapshots(project_id: str, limit: int = 10, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select
              source_ref,
              project_id,
              source_kind,
              project_summary,
              raw_text,
              competitor,
              region,
              display_label,
              status,
              processing_summary,
              key_takeaway,
              business_impact,
              linked_task_titles_json,
              source_confidence,
              signal_count,
              knowledge_count,
              last_used_in_checklist,
              created_at
            from source_snapshots
            where project_id = ?
            order by created_at desc
            limit ?
            """,
            (project_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_source_snapshot(project_id: str, source_ref: str, path: str | None = None) -> dict[str, Any] | None:
    with _connect(path) as connection:
        row = connection.execute(
            """
            select
              source_ref,
              project_id,
              source_kind,
              project_summary,
              raw_text,
              competitor,
              region,
              source_hash,
              display_label,
              status,
              processing_summary,
              key_takeaway,
              business_impact,
              linked_task_titles_json,
              source_confidence,
              signal_count,
              knowledge_count,
              last_used_in_checklist,
              created_at
            from source_snapshots
            where project_id = ? and source_ref = ?
            """,
            (project_id, source_ref),
        ).fetchone()
    return dict(row) if row else None


def update_source_snapshot(source_ref: str, updates: dict[str, Any], path: str | None = None) -> None:
    if not updates:
        return
    allowed = {
        "display_label",
        "status",
        "processing_summary",
        "key_takeaway",
        "business_impact",
        "linked_task_titles_json",
        "source_confidence",
        "signal_count",
        "knowledge_count",
        "last_used_in_checklist",
        "competitor",
        "region",
    }
    assignments = []
    params: list[Any] = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        if value is None:
            continue
        assignments.append(f"{key} = ?")
        params.append(value)
    if not assignments:
        return
    params.append(source_ref)
    with _connect(path) as connection:
        connection.execute(
            f"""
            update source_snapshots
            set {', '.join(assignments)}
            where source_ref = ?
            """,
            params,
        )


def delete_source_snapshot(project_id: str, source_ref: str, path: str | None = None) -> None:
    with _connect(path) as connection:
        connection.execute("delete from system_observations where project_id = ? and source_ref = ?", (project_id, source_ref))
        connection.execute("delete from source_snapshots where project_id = ? and source_ref = ?", (project_id, source_ref))


def list_observations_for_source(project_id: str, source_ref: str, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select
              signal_id,
              project_id,
              competitor,
              region,
              signal_type,
              summary,
              source_ref,
              observed_at,
              confidence,
              business_impact
            from system_observations
            where project_id = ? and source_ref = ? and superseded_by is null
            order by observed_at desc
            """,
            (project_id, source_ref),
        ).fetchall()
    return [dict(row) for row in rows]


def replace_draft_segments(project_id: str, segments: list[dict[str, Any]], path: str | None = None) -> None:
    with _connect(path) as connection:
        connection.execute("delete from draft_knowledge_segments where project_id = ?", (project_id,))
        for segment in segments:
            connection.execute(
                """
                insert into draft_knowledge_segments (
                  segment_id,
                  project_id,
                  segment_kind,
                  title,
                  segment_text,
                  source_refs_json,
                  evidence_refs_json,
                  importance,
                  confidence
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    segment["segment_id"],
                    project_id,
                    segment["segment_kind"],
                    segment["title"],
                    segment["segment_text"],
                    json.dumps(segment.get("source_refs", [])),
                    json.dumps(segment.get("evidence_refs", [])),
                    float(segment["importance"]),
                    float(segment["confidence"]),
                ),
            )


def list_draft_segments(project_id: str, limit: int = 24, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select
              segment_id,
              project_id,
              segment_kind,
              title,
              segment_text,
              source_refs_json,
              evidence_refs_json,
              importance,
              confidence,
              created_at,
              updated_at
            from draft_knowledge_segments
            where project_id = ?
            order by importance desc, updated_at desc
            limit ?
            """,
            (project_id, limit),
        ).fetchall()
    segments = [dict(row) for row in rows]
    for segment in segments:
        segment["source_refs"] = json.loads(segment.pop("source_refs_json") or "[]")
        segment["evidence_refs"] = json.loads(segment.pop("evidence_refs_json") or "[]")
    return segments


def upsert_draft_segment_feedback(
    project_id: str,
    segment_id: str,
    *,
    status: str,
    reason: str | None = None,
    original_payload: dict[str, Any] | None = None,
    path: str | None = None,
) -> None:
    with _connect(path) as connection:
        connection.execute(
            """
            insert into draft_segment_feedback (
              segment_id,
              project_id,
              status,
              reason,
              original_payload_json,
              updated_at
            )
            values (?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            on conflict(segment_id, project_id) do update set
              status = excluded.status,
              reason = excluded.reason,
              original_payload_json = excluded.original_payload_json,
              updated_at = excluded.updated_at
            """,
            (
                segment_id,
                project_id,
                status,
                reason,
                json.dumps(original_payload) if original_payload is not None else None,
            ),
        )


def list_draft_segment_feedback_rows(project_id: str, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select
              segment_id,
              project_id,
              status,
              reason,
              original_payload_json,
              updated_at
            from draft_segment_feedback
            where project_id = ?
            order by updated_at desc
            """,
            (project_id,),
        ).fetchall()
    feedback_rows = [dict(row) for row in rows]
    for row in feedback_rows:
        row["original_payload"] = json.loads(row.pop("original_payload_json") or "null")
    return feedback_rows


def replace_evidence_units(project_id: str, units: list[dict[str, Any]], path: str | None = None) -> None:
    with _connect(path) as connection:
        connection.execute("delete from evidence_units where project_id = ?", (project_id,))
        for unit in units:
            connection.execute(
                """
                insert into evidence_units (
                  unit_id,
                  project_id,
                  source_ref,
                  unit_kind,
                  label,
                  excerpt,
                  competitor,
                  segment,
                  channel,
                  section,
                  asset,
                  claim,
                  timing,
                  confidence
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    unit["unit_id"],
                    project_id,
                    unit["source_ref"],
                    unit["unit_kind"],
                    unit["label"],
                    unit.get("excerpt"),
                    unit.get("competitor"),
                    unit.get("segment"),
                    unit.get("channel"),
                    unit.get("section"),
                    unit.get("asset"),
                    unit.get("claim"),
                    unit.get("timing"),
                    float(unit["confidence"]),
                ),
            )


def list_evidence_units(project_id: str, limit: int = 400, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select
              unit_id,
              project_id,
              source_ref,
              unit_kind,
              label,
              excerpt,
              competitor,
              segment,
              channel,
              section,
              asset,
              claim,
              timing,
              confidence,
              created_at
            from evidence_units
            where project_id = ?
            order by confidence desc, created_at desc
            limit ?
            """,
            (project_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def list_monitor_rows(path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select
              job_name,
              last_run_at,
              last_source_ref,
              status,
              details_json,
              updated_at
            from monitor_state
            order by updated_at desc
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_managed_sources(project_id: str, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select
              source_id,
              project_id,
              label,
              source_kind,
              content_text,
              repeat_interval,
              repeat_anchor_at,
              status,
              last_run_at,
              last_result_status,
              last_result_summary,
              created_at,
              updated_at
            from managed_sources
            where project_id = ?
            order by updated_at desc
            """,
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_managed_source(source: dict[str, Any], path: str | None = None) -> None:
    with _connect(path) as connection:
        connection.execute(
            """
            insert into managed_sources (
              source_id,
              project_id,
              label,
              source_kind,
              content_text,
              repeat_interval,
              repeat_anchor_at,
              status,
              last_run_at,
              last_result_status,
              last_result_summary
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source["source_id"],
                source["project_id"],
                source["label"],
                source["source_kind"],
                source["content_text"],
                source.get("repeat_interval", "never"),
                source.get("repeat_anchor_at"),
                source["status"],
                source.get("last_run_at"),
                source.get("last_result_status"),
                source.get("last_result_summary"),
            ),
        )


def update_managed_source(source_id: str, updates: dict[str, Any], path: str | None = None) -> None:
    if not updates:
        return
    allowed = {
        "label",
        "source_kind",
        "content_text",
        "repeat_interval",
        "repeat_anchor_at",
        "status",
        "last_run_at",
        "last_result_status",
        "last_result_summary",
    }
    assignments = []
    params: list[Any] = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        assignments.append(f"{key} = ?")
        params.append(value)
    if not assignments:
        return
    assignments.append("updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')")
    params.append(source_id)
    with _connect(path) as connection:
        connection.execute(
            f"""
            update managed_sources
            set {', '.join(assignments)}
            where source_id = ?
            """,
            params,
        )


def delete_managed_source(source_id: str, path: str | None = None) -> None:
    with _connect(path) as connection:
        connection.execute("delete from managed_sources where source_id = ?", (source_id,))


def list_managed_jobs(project_id: str, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select
              managed_job_id,
              project_id,
              name,
              trigger_type,
              schedule_text,
              status,
              source_id,
              last_run_at,
              last_result_status,
              last_action_summary,
              last_expected_impact,
              last_runs_json,
              created_at,
              updated_at
            from managed_jobs
            where project_id = ?
            order by updated_at desc
            """,
            (project_id,),
        ).fetchall()
    jobs = [dict(row) for row in rows]
    for job in jobs:
      if job.get("last_runs_json"):
        try:
          job["last_runs"] = json.loads(job["last_runs_json"])
        except json.JSONDecodeError:
          job["last_runs"] = []
      else:
        job["last_runs"] = []
    return jobs


def create_managed_job(job: dict[str, Any], path: str | None = None) -> None:
    with _connect(path) as connection:
        connection.execute(
            """
            insert into managed_jobs (
              managed_job_id,
              project_id,
              name,
              trigger_type,
              schedule_text,
              status,
              source_id,
              last_run_at,
              last_result_status,
              last_action_summary,
              last_expected_impact,
              last_runs_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job["managed_job_id"],
                job["project_id"],
                job["name"],
                job["trigger_type"],
                job.get("schedule_text"),
                job["status"],
                job.get("source_id"),
                job.get("last_run_at"),
                job.get("last_result_status"),
                job.get("last_action_summary"),
                job.get("last_expected_impact"),
                json.dumps(job.get("last_runs", [])),
            ),
        )


def update_managed_job(managed_job_id: str, updates: dict[str, Any], path: str | None = None) -> None:
    if not updates:
        return
    allowed = {
        "name",
        "trigger_type",
        "schedule_text",
        "status",
        "source_id",
        "last_run_at",
        "last_result_status",
        "last_action_summary",
        "last_expected_impact",
        "last_runs_json",
    }
    assignments = []
    params: list[Any] = []
    for key, value in updates.items():
        if key == "last_runs":
            key = "last_runs_json"
            value = json.dumps(value)
        if key not in allowed:
            continue
        assignments.append(f"{key} = ?")
        params.append(value)
    if not assignments:
        return
    assignments.append("updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')")
    params.append(managed_job_id)
    with _connect(path) as connection:
        connection.execute(
            f"""
            update managed_jobs
            set {', '.join(assignments)}
            where managed_job_id = ?
            """,
            params,
        )


def delete_managed_job(managed_job_id: str, path: str | None = None) -> None:
    with _connect(path) as connection:
        connection.execute("delete from managed_jobs where managed_job_id = ?", (managed_job_id,))


def upsert_knowledge_feedback(
    project_id: str,
    knowledge_id: str,
    status: str,
    corrected_title: str | None = None,
    corrected_summary: str | None = None,
    corrected_implication: str | None = None,
    corrected_potential_moves: list[str] | None = None,
    corrected_items: list[str] | None = None,
    original_payload: dict[str, Any] | None = None,
    confidence_source: str | None = None,
    path: str | None = None,
) -> None:
    with _connect(path) as connection:
        connection.execute(
            """
            insert into knowledge_feedback (
              knowledge_id,
              project_id,
              status,
              confidence_source,
              original_payload_json,
              corrected_title,
              corrected_summary,
              corrected_implication,
              corrected_potential_moves_json,
              corrected_items_json,
              updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            on conflict(knowledge_id, project_id) do update set
              status = excluded.status,
              confidence_source = excluded.confidence_source,
              original_payload_json = coalesce(knowledge_feedback.original_payload_json, excluded.original_payload_json),
              corrected_title = excluded.corrected_title,
              corrected_summary = excluded.corrected_summary,
              corrected_implication = excluded.corrected_implication,
              corrected_potential_moves_json = excluded.corrected_potential_moves_json,
              corrected_items_json = excluded.corrected_items_json,
              updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (
                knowledge_id,
                project_id,
                status,
                confidence_source,
                json.dumps(original_payload) if original_payload is not None else None,
                corrected_title,
                corrected_summary,
                corrected_implication,
                json.dumps(corrected_potential_moves) if corrected_potential_moves is not None else None,
                json.dumps(corrected_items) if corrected_items is not None else None,
            ),
        )


def fetch_knowledge_feedback_rows(project_id: str, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select knowledge_id, project_id, status, confidence_source, original_payload_json, corrected_title, corrected_summary, corrected_implication, corrected_potential_moves_json, corrected_items_json, updated_at
            from knowledge_feedback
            where project_id = ?
            order by updated_at desc
            """,
            (project_id,),
        ).fetchall()
    feedback_rows = [dict(row) for row in rows]
    for row in feedback_rows:
        if row.get("original_payload_json"):
            try:
                row["original_payload"] = json.loads(row["original_payload_json"])
            except json.JSONDecodeError:
                row["original_payload"] = {}
        else:
            row["original_payload"] = {}
        if row.get("corrected_items_json"):
            try:
                row["corrected_items"] = json.loads(row["corrected_items_json"])
            except json.JSONDecodeError:
                row["corrected_items"] = []
        else:
            row["corrected_items"] = []
        if row.get("corrected_potential_moves_json"):
            try:
                row["corrected_potential_moves"] = json.loads(row["corrected_potential_moves_json"])
            except json.JSONDecodeError:
                row["corrected_potential_moves"] = []
        else:
            row["corrected_potential_moves"] = []
    return feedback_rows


def save_task_feedback_rows(project_id: str, job_id: str, rows: list[dict[str, Any]], path: str | None = None) -> None:
    if not rows:
        return
    with _connect(path) as connection:
        _ensure_column(connection, "task_feedback", "action_type", "text")
        for row in rows:
            connection.execute(
                """
                insert into task_feedback (
                  feedback_id,
                  task_id,
                  job_id,
                  project_id,
                  original_title,
                  original_expected_advantage,
                  feedback_type,
                  feedback_comment,
                  adjusted_text,
                  replacement_generated,
                  action_type
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["feedback_id"],
                    row.get("task_id"),
                    job_id,
                    project_id,
                    row["original_title"],
                    row.get("original_expected_advantage"),
                    row["feedback_type"],
                    row.get("feedback_comment"),
                    row.get("adjusted_text"),
                    int(bool(row.get("replacement_generated"))),
                    row.get("action_type"),
                ),
            )


def list_task_feedback_rows(project_id: str, limit: int = 80, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_column(connection, "task_feedback", "action_type", "text")
        rows = connection.execute(
            """
            select
              feedback_id,
              task_id,
              job_id,
              project_id,
              original_title,
              original_expected_advantage,
              feedback_type,
              feedback_comment,
              adjusted_text,
              replacement_generated,
              action_type,
              created_at
            from task_feedback
            where project_id = ?
            order by created_at desc
            limit ?
            """,
            (project_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def save_project_active_checklist(
    project_id: str,
    job_id: str,
    tasks: list[dict[str, Any]],
    path: str | None = None,
) -> None:
    """Persist last 3-task checklist so feedback_v2 can resolve task_id without the client sending full tasks."""
    raw = json.dumps(tasks, ensure_ascii=False)
    with _connect(path) as connection:
        connection.execute(
            """
            insert into project_active_checklist (project_id, job_id, tasks_json, updated_at)
            values (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            on conflict(project_id) do update set
              job_id = excluded.job_id,
              tasks_json = excluded.tasks_json,
              updated_at = excluded.updated_at
            """,
            (project_id, job_id, raw),
        )


def get_project_active_checklist(project_id: str, path: str | None = None) -> dict[str, Any] | None:
    with _connect(path) as connection:
        row = connection.execute(
            """
            select project_id, job_id, tasks_json, updated_at
            from project_active_checklist
            where project_id = ?
            """,
            (project_id,),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    try:
        data["tasks"] = json.loads(data["tasks_json"])
    except json.JSONDecodeError:
        data["tasks"] = []
    del data["tasks_json"]
    return data


def save_replacement_history(
    project_id: str,
    prior_task_title: str,
    replacement_title: str,
    source_feedback_id: str | None = None,
    replacement_id: str | None = None,
    path: str | None = None,
) -> None:
    with _connect(path) as connection:
        connection.execute(
            """
            insert into replacement_history (
              replacement_id,
              project_id,
              prior_task_title,
              replacement_title,
              source_feedback_id
            )
            values (?, ?, ?, ?, ?)
            """,
            (
                replacement_id or f"replacement_{project_id}_{abs(hash((prior_task_title, replacement_title, source_feedback_id)))}",
                project_id,
                prior_task_title,
                replacement_title,
                source_feedback_id,
            ),
        )


def save_generation_memory_rows(project_id: str, rows: list[dict[str, Any]], path: str | None = None) -> None:
    if not rows:
        return
    with _connect(path) as connection:
        for row in rows:
            memory_id = row.get("memory_id") or f"memory_{project_id}_{abs(hash((row['memory_kind'], row['pattern_key'], row.get('signal_value'))))}"
            connection.execute(
                """
                insert into generation_memory (
                  memory_id,
                  project_id,
                  memory_kind,
                  pattern_key,
                  signal_value,
                  weight,
                  source_feedback_id
                )
                values (?, ?, ?, ?, ?, ?, ?)
                on conflict(memory_id) do update set
                  weight = excluded.weight,
                  source_feedback_id = excluded.source_feedback_id,
                  updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                """,
                (
                    memory_id,
                    project_id,
                    row["memory_kind"],
                    row["pattern_key"],
                    row.get("signal_value"),
                    float(row.get("weight") or 1.0),
                    row.get("source_feedback_id"),
                ),
            )


def list_generation_memory_rows(project_id: str, limit: int = 200, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select
              memory_id,
              project_id,
              memory_kind,
              pattern_key,
              signal_value,
              weight,
              source_feedback_id,
              created_at,
              updated_at
            from generation_memory
            where project_id = ?
            order by updated_at desc, created_at desc
            limit ?
            """,
            (project_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_generation_memory_row(memory_id: str, project_id: str, path: str | None = None) -> bool:
    """Remove a single learned signal. Returns True if a row was deleted."""
    with _connect(path) as connection:
        cursor = connection.execute(
            "delete from generation_memory where memory_id = ? and project_id = ?",
            (memory_id, project_id),
        )
    return cursor.rowcount > 0


def clear_generation_memory(project_id: str, path: str | None = None) -> int:
    """Wipe all learned signals for a project. Returns the count of rows removed."""
    with _connect(path) as connection:
        cursor = connection.execute(
            "delete from generation_memory where project_id = ?",
            (project_id,),
        )
    return cursor.rowcount


def decay_generation_memory(project_id: str, path: str | None = None) -> None:
    """
    Called whenever generation_memory rows are loaded for generation.
    - Increments use_count for all rows used.
    - Halves weight when use_count reaches multiples of 10.
    - Removes rows where weight drops below 0.1.
    - Caps cumulative avoid_bucket/avoid_channel weight per project at 5.0 total.
    """
    with _connect(path) as connection:
        # Ensure use_count column exists (migration guard)
        _ensure_column(connection, "generation_memory", "use_count", "integer not null default 0")
        # Increment use_count for all rows belonging to this project
        connection.execute(
            "update generation_memory set use_count = use_count + 1 where project_id = ?",
            (project_id,),
        )
        # Halve weight when use_count is a multiple of 10
        connection.execute(
            """
            update generation_memory
            set weight = weight * 0.5,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            where project_id = ?
              and use_count > 0
              and (use_count % 10) = 0
            """,
            (project_id,),
        )
        # Remove fully decayed rows
        connection.execute(
            "delete from generation_memory where project_id = ? and weight < 0.1",
            (project_id,),
        )
        # Cap cumulative avoid weight: if sum of avoid_bucket + avoid_channel weight > 5.0,
        # scale all down proportionally.
        avoid_rows = connection.execute(
            """
            select memory_id, weight
            from generation_memory
            where project_id = ?
              and memory_kind in ('avoid_bucket', 'avoid_channel', 'avoid_phrase')
            order by weight desc
            """,
            (project_id,),
        ).fetchall()
        total_avoid_weight = sum(r["weight"] for r in avoid_rows)
        if total_avoid_weight > 5.0:
            scale = 5.0 / total_avoid_weight
            for row in avoid_rows:
                new_weight = row["weight"] * scale
                if new_weight < 0.1:
                    connection.execute(
                        "delete from generation_memory where memory_id = ?",
                        (row["memory_id"],),
                    )
                else:
                    connection.execute(
                        "update generation_memory set weight = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') where memory_id = ?",
                        (new_weight, row["memory_id"]),
                    )


def initialize_held_tasks_table(connection: sqlite3.Connection) -> None:
    """Ensure the held_tasks table exists (called from initialize_local_store)."""
    connection.execute(
        """
        create table if not exists held_tasks (
          held_task_id text primary key,
          project_id text not null,
          original_title text not null,
          original_rank integer,
          held_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
          status text not null default 'held'
        )
        """
    )


def save_held_task(
    project_id: str,
    held_task_id: str,
    title: str,
    rank: int | None = None,
    path: str | None = None,
) -> None:
    with _connect(path) as connection:
        initialize_held_tasks_table(connection)
        connection.execute(
            """
            insert into held_tasks (held_task_id, project_id, original_title, original_rank, status)
            values (?, ?, ?, ?, 'held')
            on conflict(held_task_id) do nothing
            """,
            (held_task_id, project_id, title, rank),
        )


def list_held_tasks(project_id: str, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        initialize_held_tasks_table(connection)
        rows = connection.execute(
            """
            select held_task_id, project_id, original_title, original_rank, held_at, status
            from held_tasks
            where project_id = ? and status = 'held'
            order by held_at desc
            """,
            (project_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def restore_held_task(held_task_id: str, project_id: str, path: str | None = None) -> bool:
    with _connect(path) as connection:
        initialize_held_tasks_table(connection)
        cursor = connection.execute(
            "update held_tasks set status = 'restored' where held_task_id = ? and project_id = ?",
            (held_task_id, project_id),
        )
    return cursor.rowcount > 0


def replace_atomic_facts(project_id: str, facts: list[dict[str, Any]], path: str | None = None) -> None:
    with _connect(path) as connection:
        connection.execute("delete from atomic_facts where project_id = ?", (project_id,))
        for fact in facts:
            connection.execute(
                """
                insert into atomic_facts (
                  fact_id, project_id, source_ref, fact_type, fact_key, fact_value_json,
                  clause_text, trace_ref, confidence
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact["fact_id"],
                    project_id,
                    fact.get("source_ref") or "",
                    fact.get("fact_type") or "observation",
                    fact.get("fact_key") or "unknown",
                    json.dumps(fact.get("fact_value"), ensure_ascii=False),
                    fact.get("clause_text"),
                    fact.get("trace_ref"),
                    float(fact.get("confidence", 0.5)),
                ),
            )


def list_atomic_facts(project_id: str, limit: int = 500, path: str | None = None) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select fact_id, project_id, source_ref, fact_type, fact_key, fact_value_json, clause_text, trace_ref, confidence, created_at
            from atomic_facts
            where project_id = ?
            order by created_at desc
            limit ?
            """,
            (project_id, max(1, limit)),
        ).fetchall()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        try:
            item["fact_value"] = json.loads(item.pop("fact_value_json"))
        except Exception:
            item["fact_value"] = item.pop("fact_value_json")
        output.append(item)
    return output


def upsert_intelligence_cards(
    project_id: str,
    cards: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    path: str | None = None,
) -> None:
    score_by_card = {str(score["card_id"]): score for score in scores}
    with _connect(path) as connection:
        for card in cards:
            card_id = str(card["card_id"])
            connection.execute(
                """
                insert into intelligence_cards (
                  card_id, project_id, insight, implication, potential_moves_json, segment, competitor, channel,
                  fact_refs_json, source_refs_json, state, expires_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(card_id) do update set
                  insight = excluded.insight,
                  implication = excluded.implication,
                  potential_moves_json = excluded.potential_moves_json,
                  segment = excluded.segment,
                  competitor = excluded.competitor,
                  channel = excluded.channel,
                  fact_refs_json = excluded.fact_refs_json,
                  source_refs_json = excluded.source_refs_json,
                  state = excluded.state,
                  expires_at = excluded.expires_at,
                  updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                """,
                (
                    card_id,
                    project_id,
                    card.get("insight") or "",
                    card.get("implication") or "",
                    json.dumps(card.get("potential_moves", []), ensure_ascii=False),
                    card.get("segment"),
                    card.get("competitor"),
                    card.get("channel"),
                    json.dumps(card.get("fact_refs", []), ensure_ascii=False),
                    json.dumps(card.get("source_refs", []), ensure_ascii=False),
                    card.get("state", "candidate"),
                    card.get("expires_at"),
                ),
            )
            score = score_by_card.get(card_id)
            if score:
                q_reason = score.get("quarantine_reason")
                g_flags = score.get("gate_flags_json")
                if g_flags is not None and not isinstance(g_flags, str):
                    g_flags = json.dumps(g_flags, ensure_ascii=False)
                connection.execute(
                    """
                    insert into card_scores (
                      card_id, project_id, confidence, impact_score, freshness_score, evidence_strength, rank_score,
                      quarantine_reason, gate_flags_json
                    )
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(card_id) do update set
                      confidence = excluded.confidence,
                      impact_score = excluded.impact_score,
                      freshness_score = excluded.freshness_score,
                      evidence_strength = excluded.evidence_strength,
                      rank_score = excluded.rank_score,
                      quarantine_reason = excluded.quarantine_reason,
                      gate_flags_json = excluded.gate_flags_json,
                      scored_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    """,
                    (
                        card_id,
                        project_id,
                        float(score.get("confidence", 0.5)),
                        float(score.get("impact_score", 50.0)),
                        float(score.get("freshness_score", 0.5)),
                        float(score.get("evidence_strength", 0.5)),
                        float(score.get("rank_score", 0.0)),
                        q_reason,
                        g_flags,
                    ),
                )


def record_flashcard_pipeline_run(
    job_id: str,
    project_id: str,
    pipeline_source: str,
    *,
    reason: str | None = None,
    detail: dict[str, Any] | None = None,
    path: str | None = None,
) -> None:
    """Persist how flashcards were produced for this job (IMP-04 transparency)."""
    run_id = str(uuid.uuid4())
    detail_json = json.dumps(detail or {}, ensure_ascii=False)
    with _connect(path) as connection:
        connection.execute(
            """
            insert into flashcard_pipeline_runs (
              run_id, job_id, project_id, pipeline_source, reason, detail_json
            )
            values (?, ?, ?, ?, ?, ?)
            """,
            (run_id, job_id, project_id, pipeline_source, reason or "", detail_json),
        )


def record_trinity_atom_progress(
    project_id: str,
    job_id: str,
    stage: str,
    payload: dict[str, Any],
    *,
    atom_index: int = -1,
    path: str | None = None,
) -> None:
    """TR-R05: append-only audit of per-atom Trinity stages (optional; TRINITY_PROGRESS_PERSIST=1)."""
    row_id = str(uuid.uuid4())
    blob = json.dumps(payload, ensure_ascii=False)
    with _connect(path) as connection:
        connection.execute(
            """
            insert into trinity_atom_progress (row_id, project_id, job_id, atom_index, stage, payload_json)
            values (?, ?, ?, ?, ?, ?)
            """,
            (row_id, project_id, job_id, atom_index, stage, blob),
        )


def latest_flashcard_pipeline_run(project_id: str, path: str | None = None) -> dict[str, Any] | None:
    """Most recent flashcard pipeline audit row for workspace / API (TR-R08)."""
    with _connect(path) as connection:
        row = connection.execute(
            """
            select run_id, job_id, project_id, pipeline_source, reason, detail_json, created_at
            from flashcard_pipeline_runs
            where project_id = ?
            order by created_at desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["detail"] = json.loads(d.pop("detail_json") or "{}")
    except json.JSONDecodeError:
        d["detail"] = {}
    return d


def list_intelligence_cards(project_id: str, include_hidden: bool = True, path: str | None = None) -> list[dict[str, Any]]:
    where = "where c.project_id = ?"
    if not include_hidden:
        where += " and c.state = 'active'"
    with _connect(path) as connection:
        rows = connection.execute(
            f"""
            select
              c.card_id,
              c.project_id,
              c.insight,
              c.implication,
              c.potential_moves_json,
              c.segment,
              c.competitor,
              c.channel,
              c.fact_refs_json,
              c.source_refs_json,
              c.state,
              c.expires_at,
              c.updated_at,
              coalesce(s.confidence, 0.0) as confidence,
              coalesce(s.impact_score, 0.0) as impact_score,
              coalesce(s.freshness_score, 0.0) as freshness_score,
              coalesce(s.evidence_strength, 0.0) as evidence_strength,
              coalesce(s.rank_score, 0.0) as rank_score,
              s.quarantine_reason as quarantine_reason,
              s.gate_flags_json as gate_flags_json
            from intelligence_cards c
            left join card_scores s on s.card_id = c.card_id
            {where}
            order by s.rank_score desc, c.updated_at desc
            """,
            (project_id,),
        ).fetchall()
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["potential_moves"] = json.loads(item.pop("potential_moves_json") or "[]")
        item["fact_refs"] = json.loads(item.pop("fact_refs_json") or "[]")
        item["source_refs"] = json.loads(item.pop("source_refs_json") or "[]")
        gf_raw = item.pop("gate_flags_json", None)
        if isinstance(gf_raw, str) and gf_raw.strip():
            try:
                item["gate_flags"] = json.loads(gf_raw)
            except json.JSONDecodeError:
                item["gate_flags"] = []
        else:
            item["gate_flags"] = []
        output.append(item)
    return output


def record_card_action(
    project_id: str,
    card_id: str,
    action_type: str,
    note: str | None = None,
    path: str | None = None,
) -> None:
    action_id = f"{project_id}:{card_id}:{action_type}:{int(datetime_now_epoch_ms())}"
    with _connect(path) as connection:
        connection.execute(
            """
            insert into card_actions (action_id, card_id, project_id, action_type, note)
            values (?, ?, ?, ?, ?)
            """,
            (action_id, card_id, project_id, action_type, note),
        )
        if action_type == "delete_and_forget":
            new_state = "deleted_forget"
        elif action_type == "delete_and_teach":
            new_state = "deleted_teach"
        else:
            new_state = None
        if new_state:
            connection.execute(
                "update intelligence_cards set state = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') where card_id = ? and project_id = ?",
                (new_state, card_id, project_id),
            )


def upsert_card_weight_profile(
    project_id: str,
    w_confidence: float,
    w_impact: float,
    w_urgency: float,
    sample_count: int,
    path: str | None = None,
) -> None:
    with _connect(path) as connection:
        connection.execute(
            """
            insert into card_weight_profiles (project_id, w_confidence, w_impact, w_urgency, sample_count)
            values (?, ?, ?, ?, ?)
            on conflict(project_id) do update set
              w_confidence = excluded.w_confidence,
              w_impact = excluded.w_impact,
              w_urgency = excluded.w_urgency,
              sample_count = excluded.sample_count,
              updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (project_id, w_confidence, w_impact, w_urgency, sample_count),
        )


def get_card_weight_profile(project_id: str, path: str | None = None) -> dict[str, Any]:
    with _connect(path) as connection:
        row = connection.execute(
            """
            select project_id, w_confidence, w_impact, w_urgency, sample_count, updated_at
            from card_weight_profiles
            where project_id = ?
            limit 1
            """,
            (project_id,),
        ).fetchone()
    if not row:
        return {
            "project_id": project_id,
            "w_confidence": 0.45,
            "w_impact": 0.40,
            "w_urgency": 0.15,
            "sample_count": 0,
        }
    return dict(row)


def datetime_now_epoch_ms() -> int:
    return int(time.time() * 1000)
