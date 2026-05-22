#!/usr/bin/env python3
"""Unified query pipeline for retrieval + answerability.

This module is the stable entry point that later FastAPI routes or LLM answer
generation can call. It does not generate natural-language answers yet.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.answerability import AnswerabilityGate
from backend.app.retriever import HybridRetriever, SearchResult


NEXT_ACTIONS = {
    "answerable": "answer_from_course_evidence",
    "needs_time_context": "answer_with_time_context",
    "needs_clarification": "ask_clarifying_question",
    "weak_evidence": "return_insufficient_course_evidence",
    "out_of_scope": "refuse_or_consider_web_fallback",
}


class QueryPipeline:
    """Run retrieval and answerability in one stable interface."""

    def __init__(
        self,
        chunks_path: Path = Path("data/phase_a/course_chunks.jsonl"),
        cache_dir: Path = Path("backend/indexes"),
        top_k: int = 5,
    ):
        self.retriever = HybridRetriever(chunks_path=chunks_path, cache_dir=cache_dir)
        self.gate = AnswerabilityGate()
        self.top_k = top_k

    def ask(self, query: str, top_k: int | None = None, short_memory: list[dict] | None = None) -> dict:
        retrieval_query = self._contextual_query(query, short_memory or [])
        results = self.retriever.search(retrieval_query, top_k=top_k or self.top_k)
        decision = self.gate.decide(query, results)
        return {
            "query": query,
            "retrieval_query": retrieval_query,
            "status": decision.status,
            "next_action": NEXT_ACTIONS.get(decision.status, "inspect_manually"),
            "reason": decision.reason,
            "confidence": decision.confidence,
            "needs_temporal_context": decision.needs_temporal_context,
            "temporal_context": decision.temporal_context,
            "multi_source": decision.multi_source,
            "evidence": [self._format_evidence(result) for result in results],
        }

    @staticmethod
    def _contextual_query(query: str, short_memory: list[dict]) -> str:
        """Use short memory for retrieval when the current query is referential."""
        lowered = query.lower()
        referential = any(token in lowered.split() for token in {"it", "this", "that", "they", "them"})
        if not referential or not short_memory:
            return query

        recent = []
        for item in short_memory[-4:]:
            role = item.get("role")
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                recent.append(content[:400])

        if not recent:
            return query
        return " ".join(recent + [query])

    @staticmethod
    def _format_evidence(result: SearchResult) -> dict:
        return {
            "chunk_id": result.chunk_id,
            "file_path": result.file_path,
            "title": result.title,
            "module": result.module,
            "score": result.score,
            "bm25_score": result.bm25_score,
            "embedding_score": result.embedding_score,
            "time_sensitive": result.time_sensitive,
            "temporal_context": result.temporal_context,
            "content": result.content,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the unified query pipeline.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--chunks", type=Path, default=Path("data/phase_a/course_chunks.jsonl"))
    parser.add_argument("--cache-dir", type=Path, default=Path("backend/indexes"))
    args = parser.parse_args()

    pipeline = QueryPipeline(chunks_path=args.chunks, cache_dir=args.cache_dir, top_k=args.top_k)
    print(json.dumps(pipeline.ask(args.query), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
