#!/usr/bin/env python3
"""Standalone Nexus web application backed by the existing course RAG."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context


REPO_ROOT = Path(__file__).resolve().parents[1]
NEXUS_ROOT = Path(__file__).resolve().parent
DIST_DIR = NEXUS_ROOT / "dist"
GRAPH_PATH = NEXUS_ROOT / "data/course_graph.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.answer_generator import AnswerGenerator, load_env_file, provider_from_name
from backend.app.prompt_builder import PromptBuilder
from backend.app.query_pipeline import QueryPipeline


def default_provider() -> str:
    if os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return "dry_run"


def default_model(provider: str) -> str | None:
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    if provider == "openai":
        return os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    if provider == "gemini":
        return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    return None


COURSE_SITE_BASE = "https://mle4217-5219.matsci.dev/"


def course_source_url(file_path: str) -> str:
    """Map a retrieved course file to its published MyST page."""
    normalized = str(file_path or "").strip().replace("\\", "/")
    normalized = re.sub(r"^(?:\./)+", "", normalized).lstrip("/")
    normalized = re.sub(r"\.(?:md|ipynb|myst|rst)$", "", normalized, flags=re.IGNORECASE)
    if normalized.lower() in {"index", "readme"}:
        normalized = ""
    elif normalized.lower().endswith(("/index", "/readme")):
        normalized = normalized.rsplit("/", 1)[0]
    encoded_path = "/".join(quote(part) for part in normalized.split("/") if part)
    return COURSE_SITE_BASE if not encoded_path else f"{COURSE_SITE_BASE}{encoded_path}/"


def create_app() -> Flask:
    load_env_file(REPO_ROOT / ".env")
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes_by_id = {node["id"]: node for node in graph["nodes"]}
    pipeline = QueryPipeline(top_k=5)
    prompt_builder = PromptBuilder(evidence_score_threshold=0.60, presentation_mode="direct")
    app = Flask(__name__, static_folder=None)

    def selected_context(payload: dict) -> list[str]:
        context = []
        for node_id in payload.get("context_node_ids", [])[:4]:
            node = nodes_by_id.get(str(node_id))
            if node:
                context.append(f"{node['type']}: {node['label']}")
        return context

    @app.get("/")
    def index():
        return send_from_directory(DIST_DIR, "index.html")

    @app.get("/assets/<path:filename>")
    def assets(filename: str):
        return send_from_directory(DIST_DIR, filename)

    @app.get("/<path:filename>")
    def static_files(filename: str):
        if filename in {"app.js", "style.css"}:
            return send_from_directory(DIST_DIR, filename)
        return send_from_directory(DIST_DIR, "index.html")

    @app.get("/api/health")
    def health():
        provider = default_provider()
        return jsonify(
            {
                "ok": True,
                "provider": provider,
                "model": default_model(provider),
                "graph_nodes": len(graph["nodes"]),
                "graph_edges": len(graph["edges"]),
            }
        )

    @app.get("/api/graph")
    def course_graph():
        return jsonify(graph)

    @app.post("/api/answer/stream")
    def answer_stream():
        payload = request.get_json(force=True) or {}
        query = str(payload.get("query", "")).strip()
        if not query:
            return jsonify({"ok": False, "error": "Query is required."}), 400

        provider_name = default_provider()
        model = default_model(provider_name)
        memory = payload.get("short_memory") or []
        context = selected_context(payload)

        def events():
            try:
                generator = AnswerGenerator(
                    pipeline=pipeline,
                    prompt_builder=prompt_builder,
                    provider=provider_from_name(provider_name, model=model),
                )
                for event in generator.stream_answer(
                    query,
                    short_memory=memory,
                    selected_context=context,
                ):
                    if event.get("sources"):
                        event = {
                            **event,
                            "sources": [
                                {**source, "url": course_source_url(source.get("file_path", ""))}
                                for source in event["sources"]
                            ],
                        }
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            except Exception as exc:
                yield json.dumps(
                    {
                        "type": "error",
                        "ok": False,
                        "message": str(exc),
                        "error": type(exc).__name__,
                    },
                    ensure_ascii=False,
                ) + "\n"

        response = Response(
            stream_with_context(events()),
            content_type="application/x-ndjson; charset=utf-8",
        )
        response.headers["Cache-Control"] = "no-cache, no-transform"
        response.headers["X-Accel-Buffering"] = "no"
        return response

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5057"))
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
