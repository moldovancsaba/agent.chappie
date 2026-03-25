#!/usr/bin/env python3
"""
Pull jobs from the hosted app queue, run process_job_payload locally, POST results back.

Resilience:
- Long timeouts and retries for /complete and /workspace (large JSON, slow Neon).
- OSError / TLS resets are retried; they no longer trigger /fail after a successful local run.
- /fail is only used when process_job_payload raises (real processing errors).
"""
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
    *,
    timeout: float = 30,
) -> tuple[int, dict | None]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "x-agent-worker-secret": secret,
            # Avoid stale keep-alive sockets that sometimes RST mid-request on macOS.
            "Connection": "close",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            raw = response.read().decode("utf-8").strip()
            return status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8").strip()
        data = {"error": raw} if raw else None
        return int(exc.code), data
    except OSError as exc:
        return 0, {"error": str(exc)}


def _post_with_retries(
    api_base: str,
    path: str,
    secret: str,
    payload: dict,
    *,
    timeout: float,
    attempts: int,
    label: str,
) -> tuple[int, dict | None]:
    """POST JSON; retry on 0/5xx/429. Stop on 4xx auth/validation errors."""
    url = f"{api_base.rstrip('/')}{path}"
    last: tuple[int, dict | None] = (0, None)
    sleep_cap = float(os.environ.get("WORKER_RETRY_SLEEP_CAP_SECONDS", "90"))
    for attempt in range(attempts):
        status, data = _request_json(url, "POST", secret, payload, timeout=timeout)
        last = (status, data)
        if status == 200:
            return last
        if status in (400, 401, 403, 404, 422):
            return last
        wait = min(sleep_cap, 5.0 * (2**attempt))
        print(
            f"[warn] {label} attempt={attempt + 1}/{attempts} status={status} "
            f"sleep={wait:.0f}s detail={data}"
        )
        time.sleep(wait)
    return last


def _claim_with_retries(
    api_base: str,
    secret: str,
    sleep_seconds: int,
    max_attempts: int = 5,
) -> tuple[int, dict | None]:
    last: tuple[int, dict | None] = (0, None)
    claim_timeout = float(os.environ.get("WORKER_HTTP_TIMEOUT_CLAIM", "60"))
    for attempt in range(max_attempts):
        try:
            return _request_json(
                f"{api_base.rstrip('/')}/api/worker/jobs/claim",
                "POST",
                secret,
                {},
                timeout=claim_timeout,
            )
        except OSError as exc:
            print(f"[warn] claim network error attempt={attempt + 1}/{max_attempts}: {exc}")
            last = (0, {"error": str(exc)})
            time.sleep(min(60, sleep_seconds * (2**attempt)))
    return last


def _fail_job_with_retries(
    api_base: str,
    secret: str,
    job_id: str,
    detail: str,
) -> None:
    attempts = int(os.environ.get("WORKER_FAIL_ATTEMPTS", "6"))
    timeout = float(os.environ.get("WORKER_HTTP_TIMEOUT_FAIL", "60"))
    st, payload = _post_with_retries(
        api_base,
        f"/api/worker/jobs/{job_id}/fail",
        secret,
        {"error_detail": detail[:8000]},
        timeout=timeout,
        attempts=attempts,
        label="fail",
    )
    if st != 200:
        print(f"[error] could not mark job failed job_id={job_id} status={st} payload={payload}")


def main() -> None:
    configure_worker_logging()
    api_base = _required_env("APP_QUEUE_BASE_URL").rstrip("/")
    secret = _required_env("WORKER_QUEUE_SHARED_SECRET")
    sleep_seconds = int(os.environ.get("WORKER_QUEUE_POLL_SECONDS", "3"))
    worker_cfg: WorkerBridgeConfig = load_config()
    drain_once = os.environ.get("WORKER_QUEUE_DRAIN_ONCE", "").strip() == "1"

    complete_timeout = float(os.environ.get("WORKER_HTTP_TIMEOUT_COMPLETE", "600"))
    complete_attempts = int(os.environ.get("WORKER_COMPLETE_ATTEMPTS", "12"))
    workspace_timeout = float(os.environ.get("WORKER_HTTP_TIMEOUT_WORKSPACE", "300"))
    workspace_attempts = int(os.environ.get("WORKER_WORKSPACE_ATTEMPTS", "8"))

    upload_fail_message = (
        "We analyzed your document on the worker, but saving results to the app failed after several tries "
        "(usually a temporary network or hosting glitch). Please wait a minute and use Run again, or re-upload."
    )

    print(f"Worker queue consumer started. polling={api_base}/api/worker/jobs/claim")
    while True:
        status, claimed = _claim_with_retries(api_base, secret, sleep_seconds)
        if status == 204:
            if drain_once:
                print("[drain_once] queue empty; exiting 0")
                return
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
        except Exception as exc:  # noqa: BLE001
            _fail_job_with_retries(api_base, secret, job_id, str(exc))
            print(f"[error] job {job_id} failed during processing: {exc}")
            time.sleep(max(1, sleep_seconds))
            if drain_once:
                return
            continue

        cs, cp = _post_with_retries(
            api_base,
            f"/api/worker/jobs/{job_id}/complete",
            secret,
            {"job_result": result["job_result"]},
            timeout=complete_timeout,
            attempts=complete_attempts,
            label="complete",
        )
        if cs != 200:
            print(f"[error] complete failed after retries job_id={job_id} status={cs} payload={cp}")
            _fail_job_with_retries(api_base, secret, job_id, upload_fail_message)
            time.sleep(max(1, sleep_seconds))
            if drain_once:
                return
            continue

        print(f"[job] completed {job_id}")
        if project_id:
            try:
                workspace_payload = build_workspace_payload(project_id, worker_cfg)
                ws, wp = _post_with_retries(
                    api_base,
                    f"/api/worker/projects/{project_id}/workspace",
                    secret,
                    {"workspace": workspace_payload},
                    timeout=workspace_timeout,
                    attempts=workspace_attempts,
                    label="workspace",
                )
                if ws != 200:
                    print(
                        f"[warn] workspace sync failed after retries project_id={project_id}: "
                        f"status={ws} payload={wp} (tasks are still in job result)"
                    )
                else:
                    print(f"[sync] workspace pushed {project_id}")
            except Exception as sync_exc:  # noqa: BLE001
                print(f"[warn] workspace build/sync failed for {project_id}: {sync_exc}")

        if drain_once:
            print("[drain_once] finished one job; exiting 0")
            return

        time.sleep(max(1, sleep_seconds))


if __name__ == "__main__":
    main()
