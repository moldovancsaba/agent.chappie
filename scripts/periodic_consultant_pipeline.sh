#!/bin/zsh
# Periodic backfill: full pipeline for SQLite source_snapshots still in status `received`.
# launchd: com.agentchappie.consultant_backfill (StartInterval, e.g. 120s).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env.queue" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env.queue"
  set +a
fi
if [[ -f "$ROOT/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env.local"
  set +a
fi

export PYTHONPATH="${ROOT}/src:${PYTHONPATH:-}"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi

exec "$PY" "$ROOT/scripts/periodic_consultant_pipeline.py"
