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

QUEUE_CONSUMER_MARKER = "worker_queue_consumer.py"


def _queue_consumer_pids() -> list[int]:
    completed = subprocess.run(
        ["pgrep", "-f", QUEUE_CONSUMER_MARKER],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []
    pids: list[int] = []
    for line in (completed.stdout or "").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.append(int(line))
        except ValueError:
            continue
    return sorted(set(pids))


def check_queue_consumer_health(
    store: RuntimeStatusStore,
    remediate_duplicates: bool,
) -> tuple[str, list[int]]:
    """
    Returns (status, pids) where status is ok | missing | duplicate.
    When remediate_duplicates and status would be duplicate, SIGTERM extra PIDs first.
    """
    pids = _queue_consumer_pids()
    log_path = os.path.join(store.status_dir, "queue_consumer_health.jsonl")
    event: dict[str, Any] = {"checked_at": utc_now_iso(), "pids": pids, "count": len(pids)}

    if len(pids) == 0:
        event["status"] = "missing"
        _append_jsonl(log_path, event)
        store.append_watchdog_log({**event, "kind": "queue_consumer"})
        return "missing", pids

    if len(pids) > 1:
        event["status"] = "duplicate"
        if remediate_duplicates:
            keep = pids[0]
            kill_list = pids[1:]
            event["remediated"] = True
            event["kept_pid"] = keep
            event["terminated_pids"] = kill_list
            for pid in kill_list:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        _append_jsonl(log_path, event)
        store.append_watchdog_log({**event, "kind": "queue_consumer"})
        return "duplicate", pids

    event["status"] = "ok"
    _append_jsonl(log_path, event)
    return "ok", pids


def _append_jsonl(path: str, payload: dict[str, Any]) -> None:
    line = json.dumps(payload, sort_keys=True) + "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line)


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
    parser.add_argument(
        "--check-queue-consumer",
        action="store_true",
        help="Count worker_queue_consumer.py processes; log to queue_consumer_health.jsonl",
    )
    parser.add_argument(
        "--remediate-duplicate-consumers",
        action="store_true",
        help="If more than one queue consumer is running, SIGTERM all but the lowest PID (oldest)",
    )
    parser.add_argument(
        "--queue-consumer-label",
        default="com.agentchappie.queue_consumer",
        help="launchd label for the Neon queue consumer job",
    )
    parser.add_argument(
        "--kickstart-missing-queue-consumer",
        action="store_true",
        help="If no worker_queue_consumer.py process is running, launchctl kickstart the queue-consumer label",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = RuntimeStatusStore(args.status_dir)
    policy = RestartPolicy(max_restarts=args.max_restarts, window_seconds=args.window_seconds)

    exit_code = 0
    if args.check_queue_consumer:
        q_status, _ = check_queue_consumer_health(store, remediate_duplicates=args.remediate_duplicate_consumers)
        if q_status == "missing":
            exit_code = max(exit_code, 4)
            if args.kickstart_missing_queue_consumer and args.queue_consumer_label:
                kick = subprocess.run(
                    ["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{args.queue_consumer_label}"],
                    capture_output=True,
                    text=True,
                )
                kick_event = {
                    "kind": "queue_consumer_kickstart",
                    "label": args.queue_consumer_label,
                    "returncode": kick.returncode,
                    "stdout": kick.stdout,
                    "stderr": kick.stderr,
                    "logged_at": utc_now_iso(),
                }
                store.append_watchdog_log(kick_event)
                _append_jsonl(
                    os.path.join(store.status_dir, "queue_consumer_health.jsonl"),
                    kick_event,
                )
                print(json.dumps(kick_event, sort_keys=True))
        elif q_status == "duplicate":
            exit_code = max(exit_code, 5)

    if not os.path.exists(store.heartbeat_file):
        result = {"status": "missing_heartbeat", "label": args.label, "heartbeat_file": store.heartbeat_file}
        print(json.dumps(result, sort_keys=True))
        return max(exit_code, 3)

    heartbeat = store.read_heartbeat()
    heartbeat_at = parse_iso8601(heartbeat["payload"]["last_heartbeat_at"])
    now = datetime.now(timezone.utc)
    age_seconds = (now - heartbeat_at).total_seconds()

    if age_seconds <= args.stale_seconds:
        result = {"status": "healthy", "age_seconds": age_seconds, "label": args.label}
        if args.check_queue_consumer:
            result["queue_consumer_exit_hint"] = exit_code
        print(json.dumps(result, sort_keys=True))
        return exit_code

    stale_result = {"status": "stale", "age_seconds": age_seconds, "label": args.label}
    if args.check_only:
        print(json.dumps(stale_result, sort_keys=True))
        return max(exit_code, 1)

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
        return max(exit_code, 2)

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
    base = completed.returncode
    return max(exit_code, base)


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
