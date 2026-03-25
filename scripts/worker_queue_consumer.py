#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.worker_bridge import (
    WorkerBridgeConfig,
    build_workspace_payload,
    load_config,
    process_job_payload,
)
from agent_chappie.worker_logging import configure_worker_logging


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def _request_json(
    url: str,
    method: str,
    secret: str,
    payload: dict | None = None,
) -> tuple[int, dict | None]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "x-agent-worker-secret": secret,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = int(response.status)
            raw = response.read().decode("utf-8").strip()
            return status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8").strip()
        data = {"error": raw} if raw else None
        return int(exc.code), data


def main() -> None:
    configure_worker_logging()
    api_base = _required_env("APP_QUEUE_BASE_URL").rstrip("/")
    secret = _required_env("WORKER_QUEUE_SHARED_SECRET")
    sleep_seconds = int(os.environ.get("WORKER_QUEUE_POLL_SECONDS", "3"))
    worker_cfg: WorkerBridgeConfig = load_config()

    print(f"Worker queue consumer started. polling={api_base}/api/worker/jobs/claim")
    while True:
        status, claimed = _request_json(f"{api_base}/api/worker/jobs/claim", "POST", secret, {})
        if status == 204:
            time.sleep(sleep_seconds)
            continue
        if status != 200 or not isinstance(claimed, dict):
            print(f"[warn] claim failed status={status} payload={claimed}")
            time.sleep(sleep_seconds)
            continue

        job_id = str(claimed.get("job_id") or "")
        print(f"[job] claimed {job_id}")
        try:
            project_id = str(claimed.get("project_id") or "")
            payload = {
                "job_request": claimed["job_request"],
                "source_package": claimed["source_package"],
            }
            result = process_job_payload(payload, worker_cfg)
            complete_status, complete_payload = _request_json(
                f"{api_base}/api/worker/jobs/{job_id}/complete",
                "POST",
                secret,
                {"job_result": result["job_result"]},
            )
            if complete_status != 200:
                print(f"[warn] complete failed for {job_id}: status={complete_status} payload={complete_payload}")
            else:
                print(f"[job] completed {job_id}")
                if project_id:
                    try:
                        workspace_payload = build_workspace_payload(project_id, worker_cfg)
                        sync_status, sync_payload = _request_json(
                            f"{api_base}/api/worker/projects/{project_id}/workspace",
                            "POST",
                            secret,
                            {"workspace": workspace_payload},
                        )
                        if sync_status != 200:
                            print(
                                f"[warn] workspace sync failed for {project_id}: "
                                f"status={sync_status} payload={sync_payload}"
                            )
                        else:
                            print(f"[sync] workspace pushed {project_id}")
                    except Exception as sync_exc:  # noqa: BLE001
                        print(f"[warn] workspace build/sync failed for {project_id}: {sync_exc}")
        except Exception as exc:  # noqa: BLE001
            fail_status, fail_payload = _request_json(
                f"{api_base}/api/worker/jobs/{job_id}/fail",
                "POST",
                secret,
                {"error_detail": str(exc)},
            )
            print(f"[error] job {job_id} failed: {exc} (fail_status={fail_status} payload={fail_payload})")

        time.sleep(max(1, sleep_seconds))


if __name__ == "__main__":
    main()

