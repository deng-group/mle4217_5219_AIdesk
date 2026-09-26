#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/api_env.sh"
PORT="${PORT:-5057}"
NO_BROWSER=false

if [[ "${1:-}" == "--no-browser" ]]; then
  NO_BROWSER=true
elif [[ -n "${1:-}" ]]; then
  echo "Usage: ./scripts/start_nexus_test.sh [--no-browser]"
  exit 2
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing scripts/api_env.sh. Copy scripts/api_env.example.sh and add the local API key first."
  exit 1
fi

# shellcheck source=/dev/null
source "${ENV_FILE}" >/dev/null

PYTHON_CANDIDATES=()
if [[ -n "${MLE_AGENT_PYTHON:-}" ]]; then
  PYTHON_CANDIDATES+=("${MLE_AGENT_PYTHON}")
fi
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CANDIDATES+=("$(command -v python3)")
fi
PYTHON_CANDIDATES+=(
  "${REPO_ROOT}/.venv/bin/python"
  "${HOME}/miniconda3/envs/matsci/bin/python"
  "${HOME}/miniforge3/envs/matsci/bin/python"
)

PYTHON_BIN=""
for candidate in "${PYTHON_CANDIDATES[@]}"; do
  if [[ -x "${candidate}" ]] && "${candidate}" -c "import flask, numpy, sklearn, sentence_transformers" >/dev/null 2>&1; then
    PYTHON_BIN="${candidate}"
    break
  fi
done
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "No Python environment with the Nexus dependencies was found."
  echo "Activate the matsci environment or set MLE_AGENT_PYTHON to its Python executable."
  exit 1
fi

cd "${REPO_ROOT}"
"${PYTHON_BIN}" scripts/check_nexus_api.py

NEXUS_URL="http://127.0.0.1:${PORT}/?theme=light"
HEALTH_URL="http://127.0.0.1:${PORT}/api/health"

if curl -fsS --max-time 2 "${HEALTH_URL}" >/dev/null 2>&1; then
  echo "Nexus is already running: ${NEXUS_URL}"
  if [[ "${NO_BROWSER}" == false ]]; then
    if command -v open >/dev/null 2>&1; then
      open "${NEXUS_URL}"
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "${NEXUS_URL}" >/dev/null 2>&1 &
    fi
  fi
  exit 0
fi

"${PYTHON_BIN}" nexus/app.py &
SERVER_PID=$!

stop_server() {
  if kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
}
trap stop_server EXIT INT TERM

for _ in {1..120}; do
  if ! kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    echo "Nexus stopped before it became ready."
    exit 1
  fi
  if curl -fsS --max-time 2 "${HEALTH_URL}" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

if ! curl -fsS --max-time 2 "${HEALTH_URL}" >/dev/null 2>&1; then
  echo "Nexus did not become ready at ${NEXUS_URL}."
  exit 1
fi

echo "Nexus test page: ${NEXUS_URL}"
echo "The API key and model were verified before startup. Press Ctrl+C to stop."

if [[ "${NO_BROWSER}" == false ]]; then
  if command -v open >/dev/null 2>&1; then
    open "${NEXUS_URL}"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${NEXUS_URL}" >/dev/null 2>&1 &
  fi
fi

wait "${SERVER_PID}"
