#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Dork Atlas Ultimate — Development Setup ==="

# 1. Backend virtual environment
if [ ! -d "backend/.venv" ]; then
    echo "Creating Python virtualenv..."
    python3 -m venv backend/.venv
fi

echo "Installing backend dependencies..."
backend/.venv/bin/pip install -q -e "backend[dev]"

# 2. Frontend dependencies
echo "Installing frontend dependencies..."
npm --prefix frontend install --silent

echo "=== Setup complete! ==="
echo "Run './scripts/dev.sh' to start both frontend and backend."
echo "Run './scripts/test.sh' to execute the test suite."
