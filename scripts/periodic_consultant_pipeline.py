#!/usr/bin/env python3
"""
launchd-friendly tick: backfill consultant pipeline for `received` source_snapshots.

Environment:
  AGENT_CONSULTANT_BACKFILL_ENABLED — default 1; set 0 to disable
  AGENT_BACKFILL_MAX_PER_RUN — default 2
  AGENT_BACKFILL_AUTO_RESEARCH — default 0 (avoid flaky network on a timer); set 1 to enable
  APP_QUEUE_BASE_URL + WORKER_QUEUE_SHARED_SECRET — optional workspace POST after each success
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.consultant_backfill import backfill_received_snapshots
from agent_chappie.worker_bridge import load_config
from agent_chappie.worker_logging import configure_worker_logging


def main() -> int:
    if os.environ.get("AGENT_CONSULTANT_BACKFILL_ENABLED", "1").strip() != "1":
        return 0
    configure_worker_logging()
    cfg = load_config()
    if os.environ.get("AGENT_BACKFILL_AUTO_RESEARCH", "0").strip() != "1":
        cfg = dataclasses.replace(cfg, auto_research_enabled=False)
    max_per = int(os.environ.get("AGENT_BACKFILL_MAX_PER_RUN", "2"))
    results = backfill_received_snapshots(cfg, max_per_run=max_per, push_workspace=True)
    if results:
        print(json.dumps({"kind": "consultant_backfill", "results": results}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
