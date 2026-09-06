#!/usr/bin/env bash
# Launches the FreightFlow AI backend (FastAPI) and frontend (React/Vite) together.
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "== FreightFlow AI =="

# --- Backend setup ---
if [ ! -d "$BACKEND_DIR/venv" ]; then
  echo "Creating backend virtualenv..."
  python3 -m venv "$BACKEND_DIR/venv"
fi

echo "Installing backend dependencies..."
"$BACKEND_DIR/venv/bin/pip" install -q --upgrade pip
"$BACKEND_DIR/venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"

echo "Starting backend on http://localhost:8000 ..."
(cd "$BACKEND_DIR" && "$BACKEND_DIR/venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

# --- Frontend setup ---
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi

echo "Starting frontend on http://localhost:5173 ..."
(cd "$FRONTEND_DIR" && npm run dev -- --host 0.0.0.0 --port 5173) &
FRONTEND_PID=$!

trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM

echo ""
echo "FreightFlow AI is running:"
echo "  Backend API : http://localhost:8000  (docs at /docs)"
echo "  Dashboard   : http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both services."

wait
