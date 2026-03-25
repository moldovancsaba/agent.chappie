#!/bin/zsh
# Long-lived Neon queue consumer for consultant follow-up. Used by launchd (com.agentchappie.queue_consumer).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Secrets and queue URL (pick one):
#   1) Repo root .env.queue  (copy from ops/queue_consumer.env.example)
#   2) Repo root .env.local  (same vars as Vercel / Mac dev)
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
export PYTHONUNBUFFERED=1
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi

exec "$PY" "$ROOT/scripts/worker_queue_consumer.py"
