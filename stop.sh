#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "Stopping Chess Tutor..."

# Find pids whose working directory is our backend/frontend dir
pids_by_cwd() {
    local cwd="$1"
    for pid in $(ls /proc | grep -E '^[0-9]+$' 2>/dev/null); do
        [ "$(readlink /proc/$pid/cwd 2>/dev/null)" = "$cwd" ] && echo $pid
    done
}

# Kill Flask: absolute-path match + cwd-based fallback
pkill -TERM -f "$BACKEND_DIR/app.py" 2>/dev/null || true
BACKEND_PIDS=$(pids_by_cwd "$BACKEND_DIR")
[ -n "$BACKEND_PIDS" ] && kill -TERM $BACKEND_PIDS 2>/dev/null || true

# Kill Vite: absolute-path match + cwd-based fallback
pkill -TERM -f "$FRONTEND_DIR/node_modules/.bin/vite" 2>/dev/null || true
FRONTEND_PIDS=$(pids_by_cwd "$FRONTEND_DIR")
[ -n "$FRONTEND_PIDS" ] && kill -TERM $FRONTEND_PIDS 2>/dev/null || true

# Give processes a moment to exit cleanly
sleep 1

# Force-kill anything still holding the ports
for PORT in 5000 5173; do
    PIDS=$(lsof -ti tcp:$PORT 2>/dev/null)
    if [ -n "$PIDS" ]; then
        echo "  Port $PORT still in use — force-killing pids: $PIDS"
        kill -9 $PIDS 2>/dev/null || true
    fi
done

# Final sweep: force-kill any remaining project processes by cwd
for DIR in "$BACKEND_DIR" "$FRONTEND_DIR"; do
    PIDS=$(pids_by_cwd "$DIR")
    [ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
done

echo "Done."
