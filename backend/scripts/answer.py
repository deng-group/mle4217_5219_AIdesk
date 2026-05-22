#!/usr/bin/env python3
"""Command-line wrapper for Phase C answer generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.answer_generator import AnswerGenerator, load_env_file, provider_from_name
from backend.app.prompt_builder import PromptBuilder
from backend.app.query_pipeline import QueryPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an answer package for one query.")
    parser.add_argument("query")
    parser.add_argument("--provider", choices=["dry_run", "openai", "gemini", "anthropic"], default="dry_run")
    parser.add_argument("--model", default=None)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-evidence", type=int, default=None)
    parser.add_argument("--evidence-threshold", type=float, default=0.60)
    parser.add_argument("--memory-json", type=Path, default=None)
    parser.add_argument("--include-prompt", action="store_true")
    args = parser.parse_args()

    load_env_file(args.env_file)

    memory = []
    if args.memory_json:
        memory = json.loads(args.memory_json.read_text(encoding="utf-8"))

    generator = AnswerGenerator(
        pipeline=QueryPipeline(top_k=args.top_k),
        prompt_builder=PromptBuilder(
            max_evidence=args.max_evidence,
            evidence_score_threshold=args.evidence_threshold,
        ),
        provider=provider_from_name(args.provider, model=args.model),
    )
    try:
        result = generator.answer(args.query, short_memory=memory)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": str(exc),
                    "provider": args.provider,
                    "model": args.model,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        raise SystemExit(1) from exc
    if not args.include_prompt:
        result.pop("prompt_package", None)
        result.pop("raw_response", None)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
