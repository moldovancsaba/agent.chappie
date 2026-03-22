from __future__ import annotations

import json
import os
import sqlite3
from typing import Any


def local_db_path() -> str:
    return os.environ.get("AGENT_LOCAL_DB_PATH", "runtime_status/agent_brain.sqlite3")


def initialize_local_store(path: str | None = None) -> str:
    db_path = path or local_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as connection:
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
            """
        )
    return db_path


def _connect(path: str | None = None) -> sqlite3.Connection:
    db_path = initialize_local_store(path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def save_source_snapshot(source: dict[str, Any], source_hash: str, path: str | None = None) -> None:
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
              source_hash
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(source_ref) do update set
              project_summary = excluded.project_summary,
              raw_text = excluded.raw_text,
              competitor = excluded.competitor,
              region = excluded.region,
              source_hash = excluded.source_hash
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
            ),
        )


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
