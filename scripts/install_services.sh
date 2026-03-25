#!/bin/zsh
set -euo pipefail

ROOT="/Users/chappie/Projects/Agent.Chappie"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
RUNTIME_LABEL="com.agentchappie.runtime"
WATCHDOG_LABEL="com.agentchappie.watchdog"
QUEUE_CONSUMER_LABEL="com.agentchappie.queue_consumer"
BACKFILL_LABEL="com.agentchappie.consultant_backfill"
RUNTIME_PLIST_SRC="${ROOT}/ops/${RUNTIME_LABEL}.plist"
WATCHDOG_PLIST_SRC="${ROOT}/ops/${WATCHDOG_LABEL}.plist"
QUEUE_CONSUMER_PLIST_SRC="${ROOT}/ops/${QUEUE_CONSUMER_LABEL}.plist"
BACKFILL_PLIST_SRC="${ROOT}/ops/${BACKFILL_LABEL}.plist"
RUNTIME_PLIST_DST="${LAUNCH_AGENTS_DIR}/${RUNTIME_LABEL}.plist"
WATCHDOG_PLIST_DST="${LAUNCH_AGENTS_DIR}/${WATCHDOG_LABEL}.plist"
QUEUE_CONSUMER_PLIST_DST="${LAUNCH_AGENTS_DIR}/${QUEUE_CONSUMER_LABEL}.plist"
BACKFILL_PLIST_DST="${LAUNCH_AGENTS_DIR}/${BACKFILL_LABEL}.plist"

mkdir -p "${LAUNCH_AGENTS_DIR}" "${ROOT}/runtime_status"
chmod +x "${ROOT}/scripts/run_queue_consumer.sh" "${ROOT}/scripts/periodic_consultant_pipeline.sh" 2>/dev/null || true
cp "${RUNTIME_PLIST_SRC}" "${RUNTIME_PLIST_DST}"
cp "${WATCHDOG_PLIST_SRC}" "${WATCHDOG_PLIST_DST}"
cp "${QUEUE_CONSUMER_PLIST_SRC}" "${QUEUE_CONSUMER_PLIST_DST}"
cp "${BACKFILL_PLIST_SRC}" "${BACKFILL_PLIST_DST}"

plutil -lint "${RUNTIME_PLIST_DST}"
plutil -lint "${WATCHDOG_PLIST_DST}"
plutil -lint "${QUEUE_CONSUMER_PLIST_DST}"
plutil -lint "${BACKFILL_PLIST_DST}"

launchctl bootout "gui/$(id -u)" "${RUNTIME_PLIST_DST}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${WATCHDOG_PLIST_DST}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${QUEUE_CONSUMER_PLIST_DST}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${BACKFILL_PLIST_DST}" >/dev/null 2>&1 || true

launchctl bootstrap "gui/$(id -u)" "${RUNTIME_PLIST_DST}"
launchctl bootstrap "gui/$(id -u)" "${WATCHDOG_PLIST_DST}"
launchctl bootstrap "gui/$(id -u)" "${QUEUE_CONSUMER_PLIST_DST}"
launchctl bootstrap "gui/$(id -u)" "${BACKFILL_PLIST_DST}"

echo "Installed ${RUNTIME_LABEL}, ${WATCHDOG_LABEL}, ${QUEUE_CONSUMER_LABEL}, ${BACKFILL_LABEL}"
echo "Set APP_QUEUE_BASE_URL and WORKER_QUEUE_SHARED_SECRET in ${ROOT}/.env.queue (see ops/queue_consumer.env.example)"
