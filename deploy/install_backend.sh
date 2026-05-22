#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/mle-course-helper/backend}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$APP_DIR"

"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip wheel
"$VENV_DIR/bin/python" -m pip install -r requirements.txt

"$VENV_DIR/bin/python" backend/scripts/query.py "What is convex hull?"

echo "Backend virtualenv is ready at $VENV_DIR"
echo "Next: copy deploy/env.example to /etc/mle-course-helper.env and install the systemd service."
