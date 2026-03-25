#!/bin/bash

# start_worker_with_watcher.sh
# Starts the Agent.Chappie worker bridge API and restarts it if it crashes.

export PYTHONPATH="$(pwd)/src"
export AGENT_WORKER_PORT="${AGENT_WORKER_PORT:-9999}"

echo "Starting Agent.Chappie Worker API watcher loop on port $AGENT_WORKER_PORT..."
echo "Logs will be written to worker.log"

while true; do
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting worker process..." >> worker.log
  python "src/agent_chappie/worker_bridge.py" >> worker.log 2>&1
  
  EXIT_CODE=$?
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Worker exited with code $EXIT_CODE. Restarting in 2 seconds..." >> worker.log
  
  sleep 2
done
