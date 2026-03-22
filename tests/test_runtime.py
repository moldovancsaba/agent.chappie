from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agent_chappie.runtime import RuntimeStatusStore
from scripts.watchdog_agent import _prune_events


class RuntimeTests(unittest.TestCase):
    def test_runtime_status_store_writes_heartbeat(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeStatusStore(tmpdir)
            path = store.write_heartbeat({"pid": 123, "last_heartbeat_at": "2026-03-22T00:00:00+00:00"})
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["payload"]["pid"], 123)

    def test_prune_events_keeps_recent_restarts(self) -> None:
        now = datetime.now(timezone.utc)
        recent = {"restarted_at": now.isoformat()}
        old = {"restarted_at": (now - timedelta(seconds=400)).isoformat()}
        kept = _prune_events([recent, old], 300)
        self.assertEqual(kept, [recent])

    def test_watchdog_state_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeStatusStore(tmpdir)
            self.assertEqual(store.read_watchdog_state(), {"restart_events": []})

    def test_append_watchdog_log_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeStatusStore(tmpdir)
            store.append_watchdog_log({"status": "healthy"})
            log_path = Path(store.watchdog_log_file)
            self.assertTrue(log_path.exists())
            self.assertEqual(json.loads(log_path.read_text(encoding="utf-8")), {"status": "healthy"})


if __name__ == "__main__":
    unittest.main()
