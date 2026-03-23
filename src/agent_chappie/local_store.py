from __future__ import annotations

import json
import os
import sqlite3
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
        _ensure_column(connection, "knowledge_feedback", "confidence_source", "text")
        _ensure_column(connection, "knowledge_feedback", "original_payload_json", "text")
        _ensure_column(connection, "knowledge_feedback", "corrected_implication", "text")
        _ensure_column(connection, "knowledge_feedback", "corrected_potential_moves_json", "text")
    finally:
        connection.close()
    return db_path


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
              status,
              last_run_at,
              last_result_status,
              last_result_summary
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source["source_id"],
                source["project_id"],
                source["label"],
                source["source_kind"],
                source["content_text"],
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
