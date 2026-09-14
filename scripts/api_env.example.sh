#!/usr/bin/env bash

# Copy this file to scripts/api_env.sh, edit these values, then source it.
# The local scripts/api_env.sh file is ignored by git.
export ANTHROPIC_BASE_URL="https://claude.matsci.dev"
export ANTHROPIC_MODEL="deepseek-v4-flash"
export ANTHROPIC_AUTH_TOKEN="PASTE_YOUR_API_KEY_HERE"

# Do not let a stale key from the terminal override the value above.
unset ANTHROPIC_API_KEY

if [[ -z "${ANTHROPIC_AUTH_TOKEN}" || "${ANTHROPIC_AUTH_TOKEN}" == "PASTE_YOUR_API_KEY_HERE" ]]; then
  unset ANTHROPIC_AUTH_TOKEN
  echo "Edit ANTHROPIC_AUTH_TOKEN in scripts/api_env.sh before starting the test site."
  return 1 2>/dev/null || exit 1
fi

echo "API environment loaded: ${ANTHROPIC_BASE_URL} / ${ANTHROPIC_MODEL}"
