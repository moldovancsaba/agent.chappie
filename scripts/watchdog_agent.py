#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.runtime import RuntimeStatusStore, parse_iso8601, utc_now_iso


@dataclass(frozen=True)
class RestartPolicy:
    max_restarts: int = 3
    window_seconds: int = 300


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watchdog for Agent.Chappie runtime service")
    parser.add_argument("--status-dir", default=os.path.join(ROOT, "runtime_status"), help="Directory containing heartbeat and watchdog state")
    parser.add_argument("--stale-seconds", type=int, default=60, help="Max age of heartbeat before considering runtime stale")
    parser.add_argument("--label", default="com.agentchappie.runtime", help="launchd label to restart")
    parser.add_argument("--check-only", action="store_true", help="Only report health, do not restart")
    parser.add_argument("--max-restarts", type=int, default=3, help="Maximum restarts allowed within the rolling window")
    parser.add_argument("--window-seconds", type=int, default=300, help="Rolling window for restart storm protection")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = RuntimeStatusStore(args.status_dir)
    policy = RestartPolicy(max_restarts=args.max_restarts, window_seconds=args.window_seconds)

    if not os.path.exists(store.heartbeat_file):
        result = {"status": "missing_heartbeat", "label": args.label, "heartbeat_file": store.heartbeat_file}
        print(json.dumps(result, sort_keys=True))
        return 3

    heartbeat = store.read_heartbeat()
    heartbeat_at = parse_iso8601(heartbeat["payload"]["last_heartbeat_at"])
    now = datetime.now(timezone.utc)
    age_seconds = (now - heartbeat_at).total_seconds()

    if age_seconds <= args.stale_seconds:
        result = {"status": "healthy", "age_seconds": age_seconds, "label": args.label}
        print(json.dumps(result, sort_keys=True))
        return 0

    stale_result = {"status": "stale", "age_seconds": age_seconds, "label": args.label}
    if args.check_only:
        print(json.dumps(stale_result, sort_keys=True))
        return 1

    state = store.read_watchdog_state()
    recent_events = _prune_events(state.get("restart_events", []), policy.window_seconds)
    if len(recent_events) >= policy.max_restarts:
        blocked = {
            "status": "restart_blocked",
            "label": args.label,
            "reason": "restart_storm_protection",
            "recent_restart_count": len(recent_events),
        }
        store.append_watchdog_log({**blocked, "logged_at": utc_now_iso()})
        print(json.dumps(blocked, sort_keys=True))
        return 2

    pid = heartbeat["payload"].get("pid")
    if isinstance(pid, int):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    restart_cmd = ["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{args.label}"]
    completed = subprocess.run(restart_cmd, capture_output=True, text=True)
    event = {
        "restarted_at": utc_now_iso(),
        "label": args.label,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    recent_events.append(event)
    store.write_watchdog_state({"restart_events": recent_events})
    store.append_watchdog_log(event)
    print(json.dumps(event, sort_keys=True))
    return completed.returncode


def _prune_events(events: list[dict[str, Any]], window_seconds: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    kept = []
    for event in events:
        restarted_at = event.get("restarted_at")
        if not isinstance(restarted_at, str):
            continue
        if parse_iso8601(restarted_at) >= cutoff:
            kept.append(event)
    return kept


if __name__ == "__main__":
    raise SystemExit(main())
