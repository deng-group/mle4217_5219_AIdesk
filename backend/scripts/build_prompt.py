#!/usr/bin/env python3
"""Command-line wrapper for prompt package construction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.prompt_builder import PromptBuilder
from backend.app.query_pipeline import QueryPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a prompt package without calling an LLM.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-evidence", type=int, default=None)
    parser.add_argument("--evidence-threshold", type=float, default=0.60)
    parser.add_argument("--memory-json", type=Path, default=None)
    args = parser.parse_args()

    memory = []
    if args.memory_json:
        memory = json.loads(args.memory_json.read_text(encoding="utf-8"))

    pipeline = QueryPipeline(top_k=args.top_k)
    builder = PromptBuilder(max_evidence=args.max_evidence, evidence_score_threshold=args.evidence_threshold)
    package = builder.build(pipeline.ask(args.query, short_memory=memory), short_memory=memory)
    print(json.dumps(package, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
