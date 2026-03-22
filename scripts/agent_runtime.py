#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from typing import Any


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.runtime import RuntimeStatusStore, utc_now_iso
from agent_chappie.workflows import WorkflowOptions, run_article_summary_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Agent.Chappie runtime service loop.")
    parser.add_argument("--service", action="store_true", help="Run as a long-lived runtime process")
    parser.add_argument("--status-dir", default=os.path.join(ROOT, "runtime_status"), help="Directory for heartbeat and watchdog state")
    parser.add_argument("--heartbeat-interval", type=int, default=15, help="Seconds between heartbeat writes")
    parser.add_argument("--probe-interval", type=int, default=300, help="Seconds between optional probe runs")
    parser.add_argument("--probe-mode", choices=["none", "dry-run", "live-run"], default="none", help="Optional probe mode for service loop")
    parser.add_argument("--task", default="Fetch https://example.com and summarise it", help="Probe task to run")
    parser.add_argument("--url", default="https://example.com", help="Probe URL to run")
    parser.add_argument("--trace-dir", default=os.path.join(ROOT, "traces"), help="Trace directory for probe runs")
    parser.add_argument("--max-heartbeats", type=int, default=0, help="Exit after N heartbeats for testing; 0 means run until stopped")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status_store = RuntimeStatusStore(args.status_dir)
    stop_requested = False
    last_probe_at = 0.0
    heartbeat_count = 0
    started_at = utc_now_iso()

    def handle_signal(signum, frame) -> None:  # type: ignore[unused-argument]
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    while not stop_requested:
        now = time.time()
        payload = {
            "pid": os.getpid(),
            "mode": "service" if args.service else "manual",
            "started_at": started_at,
            "last_heartbeat_at": utc_now_iso(),
            "probe_mode": args.probe_mode,
            "last_probe_status": "not_run",
        }

        if args.probe_mode != "none" and (last_probe_at == 0.0 or now - last_probe_at >= args.probe_interval):
            payload["last_probe_status"] = run_probe(args)
            payload["last_probe_at"] = utc_now_iso()
            last_probe_at = now

        status_store.write_heartbeat(payload)
        print(json.dumps(payload, sort_keys=True))
        heartbeat_count += 1

        if args.max_heartbeats != 0 and heartbeat_count >= args.max_heartbeats:
            break
        if not args.service and args.max_heartbeats == 0:
            break
        time.sleep(args.heartbeat_interval)

    return 0


def run_probe(args: argparse.Namespace) -> str:
    result = run_article_summary_workflow(
        WorkflowOptions(
            task=args.task,
            url=args.url,
            dry_run=args.probe_mode == "dry-run",
            trace_base_dir=args.trace_dir,
        )
    )
    return result["output"]["status"]


if __name__ == "__main__":
    raise SystemExit(main())
