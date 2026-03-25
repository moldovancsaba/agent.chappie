"""
Build synthetic consultant jobs from existing source_snapshots and run process_job_payload.

Used by scripts/process_local_sources.py and periodic backfill when SQLite has raw rows
that never finished the full Trinity / NBA pipeline.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from agent_chappie.worker_bridge import WorkerBridgeConfig, process_job_payload


def utc_iso_z() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def replay_source_kind(stored: str) -> str:
    if stored == "uploaded_file":
        return "manual_text"
    return stored


def build_synthetic_consultant_payload(
    project_id: str,
    snapshot: dict[str, Any],
    *,
    job_id: str | None = None,
    app_id: str | None = None,
) -> dict[str, Any]:
    source_ref = str(snapshot["source_ref"])
    replay_kind = replay_source_kind(str(snapshot["source_kind"]))
    file_name = snapshot.get("display_label")
    app = app_id or os.environ.get("APP_ID", "app_consultant_followup")
    jid = job_id or str(uuid.uuid4())

    return {
        "job_request": {
            "job_id": jid,
            "app_id": app,
            "project_id": project_id,
            "priority_class": "normal",
            "job_class": "heavy",
            "submitted_at": utc_iso_z(),
            "requested_capability": "followup_task_recommendation",
            "input_payload": {
                "context_type": "working_document",
                "prompt": (
                    "Identify competitive signals from the ingested source and return exactly 3 actionable follow-up tasks."
                ),
                "artifacts": [{"type": "upload", "ref": source_ref}],
            },
            "requested_by": "local:consultant_replay",
            "policy_tags": ["local-replay", "backfill"],
            "source_refs": [source_ref],
        },
        "source_package": {
            "project_id": project_id,
            "source_kind": replay_kind,
            "project_summary": str(snapshot["project_summary"] or "managed_on_worker"),
            "raw_text": str(snapshot["raw_text"] or ""),
            "source_ref": source_ref,
            "competitor": snapshot.get("competitor"),
            "region": snapshot.get("region"),
            **({"file_name": str(file_name)} if file_name else {}),
        },
    }


def run_replay_payload(payload: dict[str, Any], config: WorkerBridgeConfig) -> dict[str, Any]:
    return process_job_payload(payload, config)


def post_workspace_to_host(project_id: str, workspace: dict[str, Any]) -> tuple[int, str]:
    """POST workspace to hosted app (same contract as worker_queue_consumer)."""
    import urllib.error
    import urllib.request

    base = (os.environ.get("APP_QUEUE_BASE_URL") or "").strip().rstrip("/")
    secret = (os.environ.get("WORKER_QUEUE_SHARED_SECRET") or "").strip()
    if not base or not secret:
        return 0, "skipped_no_app_queue_env"

    url = f"{base}/api/worker/projects/{project_id}/workspace"
    body = json.dumps({"workspace": workspace}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-agent-worker-secret": secret,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
            return int(response.status), raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return int(exc.code), raw
