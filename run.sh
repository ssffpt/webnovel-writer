#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
APP_DIR="$SCRIPT_DIR/webnovel-writer"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"

if [ ! -d "$VENV_DIR" ]; then
    echo "venv 不存在，正在创建 Python 3.11 venv..."
    python3.11 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
fi

export WEBNOVEL_PROJECT_ROOT="${WEBNOVEL_PROJECT_ROOT:-}"

cd "$APP_DIR"
exec "$VENV_DIR/bin/uvicorn" dashboard.app:create_app \
    --factory \
    --host "$HOST" \
    --port "$PORT" \
    "$@"
