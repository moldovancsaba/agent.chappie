#!/bin/zsh
set -euo pipefail

ROOT="/Users/chappie/Projects/Agent.Chappie"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
RUNTIME_LABEL="com.agentchappie.runtime"
WATCHDOG_LABEL="com.agentchappie.watchdog"
RUNTIME_PLIST_DST="${LAUNCH_AGENTS_DIR}/${RUNTIME_LABEL}.plist"
WATCHDOG_PLIST_DST="${LAUNCH_AGENTS_DIR}/${WATCHDOG_LABEL}.plist"

launchctl bootout "gui/$(id -u)" "${WATCHDOG_PLIST_DST}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${RUNTIME_PLIST_DST}" >/dev/null 2>&1 || true

rm -f "${WATCHDOG_PLIST_DST}" "${RUNTIME_PLIST_DST}"

echo "Removed ${RUNTIME_LABEL} and ${WATCHDOG_LABEL}"
