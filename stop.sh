#!/usr/bin/env bash

echo "Stopping Chess Tutor..."

# Kill Flask (app.py on port 5000)
FLASK_PIDS=$(lsof -ti tcp:5000 2>/dev/null)
if [ -n "$FLASK_PIDS" ]; then
    echo "  Stopping Flask (pids: $FLASK_PIDS)"
    kill $FLASK_PIDS 2>/dev/null || true
else
    echo "  Flask not running"
fi

# Kill Vite dev server (port 5173)
VITE_PIDS=$(lsof -ti tcp:5173 2>/dev/null)
if [ -n "$VITE_PIDS" ]; then
    echo "  Stopping Vite (pids: $VITE_PIDS)"
    kill $VITE_PIDS 2>/dev/null || true
else
    echo "  Vite not running"
fi

echo "Done."
