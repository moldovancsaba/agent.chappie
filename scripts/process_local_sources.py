#!/usr/bin/env python3
"""
Run the full consultant pipeline locally from data already in SQLite:

  ingest → atomic facts → Trinity/heuristic flashcards → intelligence cards
  → knowledge / segments → NBA (or segment checklist) → updates source_snapshots

This does NOT read the Neon queue. Use when raw text is already in
`source_snapshots` (e.g. after an upload synced locally, or tests).

Optional: POST workspace JSON to the hosted app (same as queue consumer sync).

Examples:
  PYTHONPATH=src python scripts/process_local_sources.py --project-id demo_project_ah6b4mz2
  PYTHONPATH=src python scripts/process_local_sources.py --project-id demo_project_ah6b4mz2 \\
    --source-ref managed_source_src_17y3m0oy \\
    --app-base-url https://your-app.vercel.app \\
    --worker-secret \"$WORKER_QUEUE_SHARED_SECRET\"
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.consultant_local_replay import (
    build_synthetic_consultant_payload,
    post_workspace_to_host,
    run_replay_payload,
)
from agent_chappie.local_store import get_source_snapshot, initialize_local_store, list_recent_source_snapshots
from agent_chappie.worker_bridge import build_workspace_payload, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full worker pipeline from local source_snapshots.")
    parser.add_argument("--project-id", required=True, help="project_id in source_snapshots")
    parser.add_argument("--source-ref", help="Specific source_ref; default = newest row for project")
    parser.add_argument("--list", action="store_true", help="List source_ref + display_label for project and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print synthetic payload JSON and exit")
    parser.add_argument(
        "--app-base-url",
        help="Hosted app origin (e.g. https://....vercel.app). With --worker-secret, POST workspace after run.",
    )
    parser.add_argument(
        "--worker-secret",
        default=os.environ.get("WORKER_QUEUE_SHARED_SECRET", "").strip() or None,
        help="x-agent-worker-secret for workspace POST (default: env WORKER_QUEUE_SHARED_SECRET)",
    )
    parser.add_argument(
        "--no-auto-research",
        action="store_true",
        help="Disable AGENT_AUTO_RESEARCH web fetches (offline / flaky network safe).",
    )
    args = parser.parse_args()

    cfg = load_config()
    if args.no_auto_research:
        cfg = dataclasses.replace(cfg, auto_research_enabled=False)
    db_path = cfg.local_db_path
    initialize_local_store(db_path)

    rows = list_recent_source_snapshots(args.project_id, limit=80, path=db_path)
    if not rows:
        print(f"No source_snapshots for project_id={args.project_id!r} in {db_path}", file=sys.stderr)
        return 1

    if args.list:
        for row in rows:
            print(f"{row['source_ref']}\t{row.get('display_label') or ''}\t{row.get('source_kind')}\t{row.get('created_at')}")
        return 0

    if args.source_ref:
        snap = get_source_snapshot(args.project_id, args.source_ref, path=db_path)
        if not snap:
            print(f"Unknown source_ref={args.source_ref!r} for project", file=sys.stderr)
            return 1
        snapshot = snap
    else:
        primary = [r for r in rows if str(r.get("source_kind") or "") != "auto_research_url"]
        pool = primary or rows
        snapshot = max(pool, key=lambda r: str(r.get("created_at") or ""))

    app_id = os.environ.get("APP_ID", "app_consultant_followup")
    job_id = str(uuid.uuid4())
    payload = build_synthetic_consultant_payload(args.project_id, snapshot, job_id=job_id, app_id=app_id)

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"DB: {db_path}")
    print(f"project_id={args.project_id} source_ref={snapshot['source_ref']} job_id={job_id}")
    out = run_replay_payload(payload, cfg)
    jr = out["job_result"]
    print(f"status={jr['status']} completed_at={jr.get('completed_at')}")
    if jr["status"] == "complete":
        tasks = jr["result_payload"].get("recommended_tasks") or []
        print(f"recommended_tasks: {len(tasks)}")
        for t in tasks[:3]:
            print(f"  {t.get('rank')}. {t.get('title', '')[:100]}")
    else:
        rp = jr.get("result_payload") or {}
        print(f"result_payload: {rp!r:.500}")

    if args.app_base_url and args.worker_secret:
        ws = build_workspace_payload(args.project_id, cfg)
        status, body = _post_workspace_manual(args.app_base_url, args.worker_secret, args.project_id, ws)
        print(f"workspace POST: HTTP {status} {body[:300]}")
        if status != 200:
            return 1
    elif args.app_base_url and not args.worker_secret:
        print("Skipping workspace POST: set --worker-secret or WORKER_QUEUE_SHARED_SECRET", file=sys.stderr)
    elif not args.app_base_url:
        code, detail = post_workspace_to_host(args.project_id, build_workspace_payload(args.project_id, cfg))
        if code and code != 200 and "skipped" not in detail:
            print(f"env workspace POST: HTTP {code} {detail[:200]}")

    return 0 if jr["status"] == "complete" else 2


def _post_workspace_manual(base_url: str, secret: str, project_id: str, workspace: dict) -> tuple[int, str]:
    import urllib.error
    import urllib.request

    url = f"{base_url.rstrip('/')}/api/worker/projects/{project_id}/workspace"
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


if __name__ == "__main__":
    raise SystemExit(main())
