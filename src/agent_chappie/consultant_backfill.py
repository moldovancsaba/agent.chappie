"""
Periodic backfill: run full consultant pipeline for source_snapshots stuck in `received`.

Does not use Neon job queue. Optional workspace POST when APP_QUEUE_BASE_URL + secret are set.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from agent_chappie.local_store import initialize_local_store
from agent_chappie.worker_bridge import WorkerBridgeConfig, build_workspace_payload

from agent_chappie.consultant_local_replay import (
    build_synthetic_consultant_payload,
    post_workspace_to_host,
    run_replay_payload,
)


def list_received_snapshots(db_path: str, *, limit: int = 8) -> list[dict[str, Any]]:
    initialize_local_store(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            select source_ref, project_id, source_kind, project_summary, raw_text,
                   competitor, region, display_label, status, created_at
            from source_snapshots
            where lower(coalesce(status, '')) = 'received'
              and coalesce(source_kind, '') != 'auto_research_url'
            order by created_at asc
            limit ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def backfill_received_snapshots(
    config: WorkerBridgeConfig,
    *,
    max_per_run: int = 2,
    push_workspace: bool = True,
) -> list[dict[str, Any]]:
    """
    Process up to max_per_run rows with status `received`.
    Returns a list of outcome dicts for logging.
    """
    out: list[dict[str, Any]] = []
    rows = list_received_snapshots(config.local_db_path, limit=max_per_run)
    for snap in rows:
        project_id = str(snap["project_id"])
        source_ref = str(snap["source_ref"])
        payload = build_synthetic_consultant_payload(project_id, snap)
        job_id = payload["job_request"]["job_id"]
        try:
            result = run_replay_payload(payload, config)
            jr = result["job_result"]
            row: dict[str, Any] = {
                "project_id": project_id,
                "source_ref": source_ref,
                "job_id": job_id,
                "status": jr.get("status"),
            }
            if push_workspace and jr.get("status") == "complete":
                ws = build_workspace_payload(project_id, config)
                code, detail = post_workspace_to_host(project_id, ws)
                row["workspace_http"] = code
                row["workspace_detail"] = detail[:240] if detail else ""
            out.append(row)
        except Exception as exc:  # noqa: BLE001
            out.append(
                {
                    "project_id": project_id,
                    "source_ref": source_ref,
                    "job_id": job_id,
                    "status": "error",
                    "error": str(exc),
                }
            )
    return out
