from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


ARTIFACT_FILE_ORDER = {
    "request": "01_request.json",
    "structured_task_object": "02_structured_task_object.json",
    "execution_plan": "03_execution_plan.json",
    "decision_record": "04_decision_record.json",
    "outcome": "05_outcome.json",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class TraceStore:
    base_dir: str
    run_id: str = field(init=False)
    run_dir: str = field(init=False)

    def __post_init__(self) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.run_id = f"{timestamp}_{uuid4().hex[:8]}"
        self.run_dir = os.path.join(self.base_dir, self.run_id)
        os.makedirs(self.run_dir, exist_ok=False)

    def write_artifact(self, artifact_name: str, payload: dict[str, object]) -> str:
        if artifact_name not in ARTIFACT_FILE_ORDER:
            raise ValueError(f"Unknown artifact '{artifact_name}'")
        path = os.path.join(self.run_dir, ARTIFACT_FILE_ORDER[artifact_name])
        if os.path.exists(path):
            raise FileExistsError(f"Artifact already exists: {path}")
        wrapped_payload = {
            "artifact_name": artifact_name,
            "run_id": self.run_id,
            "written_at": utc_now_iso(),
            "payload": payload,
        }
        with open(path, "x", encoding="utf-8") as handle:
            json.dump(wrapped_payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return path
