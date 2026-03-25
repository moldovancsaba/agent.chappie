#!/bin/bash
export PYTHONPATH=src

cat /dev/null > docs/08_handoffs/proof_of_nextjs_api.md

echo "Cleaning up ports..."
pkill -f 'worker_bridge.py' || true
lsof -ti:3010 | xargs kill -9 2>/dev/null || true
lsof -ti:9999 | xargs kill -9 2>/dev/null || true

echo "Starting Python Worker Bridge API..."
source .venv/bin/activate
export AGENT_WORKER_PORT=9999
export PYTHONPATH=src
export PYTHONUNBUFFERED=1
python src/agent_chappie/worker_bridge.py > worker.log 2>&1 &
PYTHON_PID=$!
sleep 3

echo "Starting NextJS API..."
cd apps/consultant-followup-web
export PORT=3010
export AGENT_BRIDGE_MODE=worker
export AGENT_API_BASE_URL=http://localhost:9999
export AGENT_SHARED_SECRET=change-me
npm run dev > nextjs.log 2>&1 &
NEXTJS_PID=$!

sleep 58

echo "Hitting live boundary..."
cd ../../
python scripts/hit_nextjs_api.py >> docs/08_handoffs/proof_of_nextjs_api.md

echo "Shutting down servers..."
kill $PYTHON_PID
kill $NEXT_PID
wait $PYTHON_PID 2>/dev/null
wait $NEXT_PID 2>/dev/null
echo "Run complete."
