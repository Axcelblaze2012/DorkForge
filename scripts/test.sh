#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Running Frontend Vitest Suite ==="
npm --prefix frontend run test

echo "=== Running Backend Pytest Suite ==="
backend/.venv/bin/pytest backend/tests -v

echo "=== All Tests Passed! ==="
