#!/usr/bin/env python3
"""Command-line wrapper for the unified query pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.query_pipeline import QueryPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the retrieval + answerability pipeline.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--chunks", type=Path, default=Path("data/phase_a/course_chunks.jsonl"))
    parser.add_argument("--cache-dir", type=Path, default=Path("backend/indexes"))
    parser.add_argument("--memory-json", type=Path, default=None)
    args = parser.parse_args()

    memory = []
    if args.memory_json:
        memory = json.loads(args.memory_json.read_text(encoding="utf-8"))

    pipeline = QueryPipeline(chunks_path=args.chunks, cache_dir=args.cache_dir, top_k=args.top_k)
    result = pipeline.ask(args.query, short_memory=memory)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
