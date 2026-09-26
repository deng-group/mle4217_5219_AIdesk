#!/usr/bin/env python3
"""Verify the configured Anthropic-compatible API without exposing credentials."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile


def main() -> None:
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "").rstrip("/")
    model = os.environ.get("ANTHROPIC_MODEL", "")
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    missing = [
        name
        for name, value in (
            ("ANTHROPIC_BASE_URL", base_url),
            ("ANTHROPIC_MODEL", model),
            ("ANTHROPIC_AUTH_TOKEN", token),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"API check failed: missing {', '.join(missing)}.")

    payload = json.dumps(
        {
            "model": model,
            "max_tokens": 64,
            "temperature": 0,
            "system": "This is a connectivity check.",
            "messages": [{"role": "user", "content": "Reply with OK."}],
        }
    ).encode("utf-8")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=True) as config:
        escaped_token = token.replace("\\", "\\\\").replace('"', '\\"')
        config.write(f'url = "{base_url}/v1/messages"\n')
        config.write('header = "content-type: application/json"\n')
        config.write('header = "anthropic-version: 2023-06-01"\n')
        config.write(f'header = "x-api-key: {escaped_token}"\n')
        config.write('request = "POST"\n')
        config.flush()
        completed = subprocess.run(
            [
                "curl",
                "-sS",
                "--fail-with-body",
                "--max-time",
                "45",
                "--config",
                config.name,
                "--data-binary",
                "@-",
            ],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if completed.returncode != 0:
        detail = (completed.stdout or completed.stderr).decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"API check failed: {detail}")
    try:
        result = json.loads(completed.stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"API check failed: invalid JSON response ({exc}).") from None

    content = result.get("content") or []
    if not any(isinstance(item, dict) and item.get("text") for item in content):
        raise SystemExit("API check failed: the endpoint returned no text content.")
    print(f"API check passed: anthropic-compatible / {model}")


if __name__ == "__main__":
    main()
