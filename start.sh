#!/bin/sh
set -eu

node /opt/pi_agent/agent_service.js &
PI_PID=$!
cleanup() { kill "$PI_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

ready=0
for _ in $(seq 1 30); do
  if node -e "fetch('http://127.0.0.1:${PI_AGENT_PORT:-8001}/health').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"; then
    ready=1
    break
  fi
  if ! kill -0 "$PI_PID" 2>/dev/null; then
    echo "[STARTUP] Pi Agent exited before becoming ready." >&2
    exit 1
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "[STARTUP] Pi Agent did not become ready within 30 seconds." >&2
  exit 1
fi

echo "[STARTUP] Pi Agent ready; starting FastAPI on port ${PORT:-8000}."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
API_PID=$!
wait "$API_PID"
