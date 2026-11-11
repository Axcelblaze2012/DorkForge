#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cleanup() {
    echo ""
    echo "Shutting down Dork Atlas development servers..."
    kill $(jobs -p) 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting Dork Atlas Backend on http://127.0.0.1:8000..."
backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000 &

echo "Starting Dork Atlas Frontend on http://127.0.0.1:5173..."
npm --prefix frontend run dev &

wait
