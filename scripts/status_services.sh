#!/bin/zsh
set -euo pipefail

ROOT="/Users/chappie/Projects/Agent.Chappie"
RUNTIME_LABEL="com.agentchappie.runtime"
WATCHDOG_LABEL="com.agentchappie.watchdog"

echo "== runtime service =="
launchctl print "gui/$(id -u)/${RUNTIME_LABEL}" || true

echo "== watchdog service =="
launchctl print "gui/$(id -u)/${WATCHDOG_LABEL}" || true

echo "== heartbeat =="
if [[ -f "${ROOT}/runtime_status/heartbeat.json" ]]; then
  cat "${ROOT}/runtime_status/heartbeat.json"
else
  echo "missing ${ROOT}/runtime_status/heartbeat.json"
fi

echo "== watchdog state =="
if [[ -f "${ROOT}/runtime_status/watchdog_state.json" ]]; then
  cat "${ROOT}/runtime_status/watchdog_state.json"
else
  echo "missing ${ROOT}/runtime_status/watchdog_state.json"
fi
