#!/usr/bin/env python3
"""
Wipe hosted (Neon) demo queue/state and reset the local worker SQLite brain.

Loads env from repo root `.env.local` then `.env.queue` (later file wins on duplicate keys).

Usage:
  python3 scripts/wipe_agent_storage.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        os.environ[key] = val


def _wipe_sqlite(db_path: Path) -> None:
    if db_path.is_file():
        db_path.unlink()
        print(f"Removed SQLite: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    src = ROOT / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from agent_chappie.local_store import initialize_local_store

    initialize_local_store(str(db_path))
    print(f"Initialized empty SQLite: {db_path}")


def _wipe_neon(database_url: str) -> None:
    # Child tables first (FKs); demo_projects last. Tables like demo_job_queue may not exist until first Neon enqueue.
    sql = """
    DO $wipe$
    BEGIN
      BEGIN DELETE FROM demo_job_queue; EXCEPTION WHEN undefined_table THEN NULL; END;
      BEGIN DELETE FROM demo_job_results; EXCEPTION WHEN undefined_table THEN NULL; END;
      BEGIN DELETE FROM demo_feedback; EXCEPTION WHEN undefined_table THEN NULL; END;
      BEGIN DELETE FROM demo_jobs; EXCEPTION WHEN undefined_table THEN NULL; END;
      BEGIN DELETE FROM demo_workspace_snapshots; EXCEPTION WHEN undefined_table THEN NULL; END;
      BEGIN DELETE FROM demo_fact_flashcard_actions; EXCEPTION WHEN undefined_table THEN NULL; END;
      BEGIN DELETE FROM demo_projects; EXCEPTION WHEN undefined_table THEN NULL; END;
    END;
    $wipe$;
    """
    result = subprocess.run(
        ["psql", database_url, "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout or "psql failed\n")
        raise SystemExit(result.returncode)
    print("Neon demo_* tables cleared (existing tables only).")


def main() -> None:
    _load_env_file(ROOT / ".env.local")
    _load_env_file(ROOT / ".env.queue")

    raw_db = os.environ.get("AGENT_LOCAL_DB_PATH", "runtime_status/agent_brain.sqlite3").strip()
    db_path = Path(raw_db)
    if not db_path.is_absolute():
        db_path = ROOT / db_path
    _wipe_sqlite(db_path.resolve())

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if db_url:
        _wipe_neon(db_url)
    else:
        print("DATABASE_URL not set; skipped Neon wipe (use Neon mode on the app for online state).")


if __name__ == "__main__":
    main()
