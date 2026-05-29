#!/usr/bin/env python3
"""Minimal web chat window for the course AI agent."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.answer_generator import AnswerGenerator, load_env_file, provider_from_name
from backend.app.prompt_builder import PromptBuilder
from backend.app.query_pipeline import QueryPipeline


def default_provider() -> str:
    if os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return "dry_run"


def default_model(provider: str) -> str:
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    if provider == "gemini":
        return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    return ""


def public_sources(sources: list[dict]) -> list[dict]:
    return [
        {
            "title": source["title"],
            "file_path": source["file_path"],
            "score": source["score"],
        }
        for source in sources
    ]


def create_app() -> Flask:
    load_env_file(REPO_ROOT / ".env")
    app = Flask(__name__)
    pipeline = QueryPipeline(top_k=5)
    prompt_builder = PromptBuilder(evidence_score_threshold=0.60)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @app.route("/api/answer", methods=["OPTIONS"])
    def answer_options():
        return ("", 204)

    @app.get("/")
    def index():
        provider = default_provider()
        return render_template(
            "index.html",
            default_provider=provider,
            default_model=default_model(provider),
        )

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "default_provider": default_provider(),
                "anthropic_configured": bool(os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")),
                "gemini_configured": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
            }
        )

    @app.post("/api/answer")
    def answer():
        payload = request.get_json(force=True) or {}
        query = str(payload.get("query", "")).strip()
        if not query:
            return jsonify({"ok": False, "error": "Query is required."}), 400

        provider = payload.get("provider") or default_provider()
        model = payload.get("model") or default_model(provider) or None
        memory = payload.get("short_memory") or []

        try:
            generator = AnswerGenerator(
                pipeline=pipeline,
                prompt_builder=prompt_builder,
                provider=provider_from_name(provider, model=model),
            )
            result = generator.answer(query, short_memory=memory)
        except Exception as exc:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": type(exc).__name__,
                        "message": str(exc),
                        "provider": provider,
                        "model": model,
                    }
                ),
                502,
            )

        return jsonify(
            {
                "ok": True,
                "query": result["query"],
                "answer": result["answer"],
                "status": result["status"],
                "llm_action": result["llm_action"],
                "provider": result["provider"],
                "model": result["model"],
                "confidence": result["confidence"],
                "temporal_context": result["temporal_context"],
                "sources": public_sources(result["sources"]),
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5055"))
    app.run(host="127.0.0.1", port=port, debug=False)
