from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class RuntimeStatusStore:
    status_dir: str
    heartbeat_file: str = field(init=False)
    watchdog_state_file: str = field(init=False)
    watchdog_log_file: str = field(init=False)

    def __post_init__(self) -> None:
        Path(self.status_dir).mkdir(parents=True, exist_ok=True)
        self.heartbeat_file = os.path.join(self.status_dir, "heartbeat.json")
        self.watchdog_state_file = os.path.join(self.status_dir, "watchdog_state.json")
        self.watchdog_log_file = os.path.join(self.status_dir, "watchdog_log.jsonl")

    def write_heartbeat(self, payload: dict[str, Any]) -> str:
        wrapped = {
            "written_at": utc_now_iso(),
            "payload": payload,
        }
        with open(self.heartbeat_file, "w", encoding="utf-8") as handle:
            json.dump(wrapped, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return self.heartbeat_file

    def read_heartbeat(self) -> dict[str, Any]:
        with open(self.heartbeat_file, encoding="utf-8") as handle:
            return json.load(handle)

    def read_watchdog_state(self) -> dict[str, Any]:
        if not os.path.exists(self.watchdog_state_file):
            return {"restart_events": []}
        with open(self.watchdog_state_file, encoding="utf-8") as handle:
            return json.load(handle)

    def write_watchdog_state(self, payload: dict[str, Any]) -> str:
        with open(self.watchdog_state_file, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return self.watchdog_state_file

    def append_watchdog_log(self, payload: dict[str, Any]) -> str:
        with open(self.watchdog_log_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")
        return self.watchdog_log_file


def parse_iso8601(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp)

