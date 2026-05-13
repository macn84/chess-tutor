#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/../my-venv"

# Load .env if present
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Install Python deps if needed
source "$VENV/bin/activate"
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# Start Flask backend
cd "$SCRIPT_DIR/backend"
python app.py &
FLASK_PID=$!

# Start Vite frontend
cd "$SCRIPT_DIR/frontend"
npm install --silent
npm run dev &
VITE_PID=$!

echo ""
echo "Chess Tutor is starting..."
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop."

cleanup() {
    echo "Shutting down..."
    kill $FLASK_PID $VITE_PID 2>/dev/null || true
    deactivate 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait $FLASK_PID $VITE_PID
