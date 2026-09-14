#!/usr/bin/env python3
"""Open the real course website with the local AI helper backend attached."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOK_REPO = REPO_ROOT.parent / "MLE4217_5219_book"
BACKEND_URL = "http://127.0.0.1:5055"


def url_ready(url: str, timeout: float = 1.0) -> bool:
    try:
        probe = request.Request(url, method="HEAD")
        with request.urlopen(probe, timeout=timeout) as response:
            return response.status < 500
    except (error.URLError, TimeoutError):
        return False


def find_backend_python(explicit: Path | None) -> Path:
    candidates = []
    configured = os.environ.get("MLE_AGENT_PYTHON")
    if explicit:
        candidates.append(explicit)
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            Path(sys.executable),
            REPO_ROOT / ".venv" / "bin" / "python",
            Path.home() / "miniconda3" / "envs" / "matsci" / "bin" / "python",
            Path.home() / "miniforge3" / "envs" / "matsci" / "bin" / "python",
        ]
    )

    seen = set()
    for candidate in candidates:
        candidate = candidate.expanduser().resolve()
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        check = subprocess.run(
            [str(candidate), "-c", "import flask, numpy, sklearn, sentence_transformers"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if check.returncode == 0:
            return candidate
    raise SystemExit(
        "No Python environment with the backend dependencies was found. "
        "Activate the matsci environment or pass --python /path/to/python."
    )


def wait_until_ready(url: str, process: subprocess.Popen | None, label: str, seconds: int = 120) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise SystemExit(f"{label} exited before it became ready (exit code {process.returncode}).")
        if url_ready(url):
            return
        time.sleep(0.25)
    raise SystemExit(f"Timed out waiting for {label} at {url}.")


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start the AI backend and open the widget inside the built MLE4217/5219 course site."
    )
    parser.add_argument("--book-repo", type=Path, default=DEFAULT_BOOK_REPO)
    parser.add_argument("--python", type=Path, help="Python executable for the RAG backend.")
    parser.add_argument(
        "--page",
        default="/",
        help="Course-page route to open, relative to the site root.",
    )
    parser.add_argument("--site-port", type=int, default=8000)
    parser.add_argument("--build", action="store_true", help="Rebuild the course book before testing.")
    parser.add_argument("--no-browser", action="store_true", help="Start services without opening a browser window.")
    args = parser.parse_args()

    book_repo = args.book_repo.expanduser().resolve()
    build_html = book_repo / "_build" / "html"
    injector = book_repo / "ai_agent_widget" / "inject_ai_agent_widget.py"
    if not (book_repo / "AGENTS.md").exists() or not injector.exists():
        raise SystemExit(f"This does not look like the MLE4217/5219 course repository: {book_repo}")

    backend_python = find_backend_python(args.python)
    if args.build:
        subprocess.run(["make", "web"], cwd=book_repo, check=True)
    elif not build_html.exists():
        raise SystemExit(f"Built course site not found at {build_html}. Re-run with --build.")

    # Copy the current widget into the existing course build without rebuilding all chapters.
    subprocess.run([str(backend_python), str(injector)], cwd=book_repo, check=True)

    backend_process = None
    site_process = None
    try:
        if url_ready(f"{BACKEND_URL}/api/health"):
            print(f"Using the backend already running at {BACKEND_URL}", flush=True)
        else:
            backend_env = os.environ.copy()
            backend_env["PORT"] = "5055"
            backend_process = subprocess.Popen(
                [str(backend_python), str(REPO_ROOT / "web_app" / "app.py")],
                cwd=REPO_ROOT,
                env=backend_env,
            )
            wait_until_ready(f"{BACKEND_URL}/api/health", backend_process, "AI backend")

        site_url = f"http://127.0.0.1:{args.site_port}"
        if url_ready(site_url):
            print(f"Using the course site already running at {site_url}", flush=True)
        else:
            site_process = subprocess.Popen(
                [str(backend_python), "-m", "http.server", str(args.site_port), "--bind", "127.0.0.1"],
                cwd=build_html,
            )
            wait_until_ready(site_url, site_process, "course site", seconds=15)

        page = args.page.strip().lstrip("/")
        test_url = f"{site_url}/{page}"
        print(f"\nCourse widget test page: {test_url}", flush=True)
        print("Use the ? button at the bottom-right. Press Ctrl+C here when finished.\n", flush=True)
        if not args.no_browser:
            webbrowser.open(test_url, new=1)

        while True:
            if backend_process is not None and backend_process.poll() is not None:
                raise SystemExit(f"AI backend stopped unexpectedly (exit code {backend_process.returncode}).")
            if site_process is not None and site_process.poll() is not None:
                raise SystemExit(f"Course site stopped unexpectedly (exit code {site_process.returncode}).")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping the local test services.", flush=True)
    finally:
        stop_process(site_process)
        stop_process(backend_process)


if __name__ == "__main__":
    main()
