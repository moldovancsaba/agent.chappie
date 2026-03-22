#!/bin/zsh
set -euo pipefail

ROOT="/Users/chappie/Projects/Agent.Chappie"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
RUNTIME_LABEL="com.agentchappie.runtime"
WATCHDOG_LABEL="com.agentchappie.watchdog"
RUNTIME_PLIST_SRC="${ROOT}/ops/${RUNTIME_LABEL}.plist"
WATCHDOG_PLIST_SRC="${ROOT}/ops/${WATCHDOG_LABEL}.plist"
RUNTIME_PLIST_DST="${LAUNCH_AGENTS_DIR}/${RUNTIME_LABEL}.plist"
WATCHDOG_PLIST_DST="${LAUNCH_AGENTS_DIR}/${WATCHDOG_LABEL}.plist"

mkdir -p "${LAUNCH_AGENTS_DIR}" "${ROOT}/runtime_status"
cp "${RUNTIME_PLIST_SRC}" "${RUNTIME_PLIST_DST}"
cp "${WATCHDOG_PLIST_SRC}" "${WATCHDOG_PLIST_DST}"

plutil -lint "${RUNTIME_PLIST_DST}"
plutil -lint "${WATCHDOG_PLIST_DST}"

launchctl bootout "gui/$(id -u)" "${RUNTIME_PLIST_DST}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${WATCHDOG_PLIST_DST}" >/dev/null 2>&1 || true

launchctl bootstrap "gui/$(id -u)" "${RUNTIME_PLIST_DST}"
launchctl bootstrap "gui/$(id -u)" "${WATCHDOG_PLIST_DST}"

echo "Installed ${RUNTIME_LABEL} and ${WATCHDOG_LABEL}"
