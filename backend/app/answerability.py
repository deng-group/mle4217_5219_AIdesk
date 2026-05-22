#!/usr/bin/env python3
"""Rule-based answerability gate for retrieved course evidence.

The gate decides whether retrieved chunks are strong enough to pass to a future
LLM answer generator. It intentionally does not generate answers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.retriever import LOGISTICS_TERMS, HybridRetriever, SearchResult, tokenize


OUT_OF_SCOPE_TERMS = {
    "cafeteria",
    "canteen",
    "menu",
    "weather",
    "stock",
    "price",
    "president",
    "restaurant",
    "flight",
    "hotel",
}

BROAD_TERMS = {
    "everything",
    "anything",
    "overview",
    "summarize",
    "summary",
    "tell",
}


@dataclass
class AnswerabilityDecision:
    query: str
    status: str
    reason: str
    needs_temporal_context: bool
    temporal_context: str | None
    multi_source: bool
    confidence: float
    top_results: list[dict]


class AnswerabilityGate:
    """Conservative rule-based gate over retrieval results."""

    def __init__(
        self,
        strong_score: float = 0.72,
        weak_score: float = 0.42,
        min_embedding_score: float = 0.18,
    ):
        self.strong_score = strong_score
        self.weak_score = weak_score
        self.min_embedding_score = min_embedding_score

    def decide(self, query: str, results: list[SearchResult]) -> AnswerabilityDecision:
        tokens = set(tokenize(query))
        top = results[0] if results else None
        temporal_context = self._temporal_context(results)
        needs_temporal_context = bool(tokens & LOGISTICS_TERMS)
        multi_source = self._is_multi_source(results)

        if not top:
            return self._decision(query, "weak_evidence", "No chunks were retrieved.", False, None, False, 0.0, results)

        if tokens & OUT_OF_SCOPE_TERMS:
            return self._decision(
                query,
                "out_of_scope",
                "The query appears outside the course knowledge base.",
                needs_temporal_context,
                temporal_context,
                multi_source,
                top.score,
                results,
            )

        if top.score < self.weak_score or (top.bm25_score <= 0.01 and top.embedding_score < self.min_embedding_score):
            return self._decision(
                query,
                "weak_evidence",
                "The retrieved chunks are too weak to support a reliable answer.",
                needs_temporal_context,
                temporal_context,
                multi_source,
                top.score,
                results,
            )

        if needs_temporal_context and not temporal_context:
            return self._decision(
                query,
                "needs_time_context",
                "The query is course-offering specific, but no syllabus/calendar time context was retrieved.",
                True,
                None,
                multi_source,
                top.score,
                results,
            )

        if tokens & BROAD_TERMS and len(tokens) <= 4:
            return self._decision(
                query,
                "needs_clarification",
                "The query is broad and should be narrowed to a concept, module, or task.",
                needs_temporal_context,
                temporal_context,
                multi_source,
                top.score,
                results,
            )

        status = "needs_time_context" if needs_temporal_context else "answerable"
        reason = "Course-offering answer should state the retrieved academic year/semester." if needs_temporal_context else "Retrieved course evidence is strong enough."
        return self._decision(
            query,
            status,
            reason,
            needs_temporal_context,
            temporal_context,
            multi_source,
            top.score,
            results,
        )

    def _decision(
        self,
        query: str,
        status: str,
        reason: str,
        needs_temporal_context: bool,
        temporal_context: str | None,
        multi_source: bool,
        confidence: float,
        results: list[SearchResult],
    ) -> AnswerabilityDecision:
        return AnswerabilityDecision(
            query=query,
            status=status,
            reason=reason,
            needs_temporal_context=needs_temporal_context,
            temporal_context=temporal_context,
            multi_source=multi_source,
            confidence=float(confidence),
            top_results=[asdict(result) for result in results],
        )

    @staticmethod
    def _temporal_context(results: list[SearchResult]) -> str | None:
        for result in results:
            if result.temporal_context and result.temporal_context.get("year"):
                return result.temporal_context["year"]
        return None

    @staticmethod
    def _is_multi_source(results: list[SearchResult]) -> bool:
        if len(results) < 2:
            return False
        top_score = results[0].score
        close_results = [result for result in results[:5] if result.score >= top_score * 0.72]
        modules = {result.module for result in close_results}
        files = {result.file_path for result in close_results}
        return len(modules) >= 2 or len(files) >= 3


def print_decision(decision: AnswerabilityDecision, display_top_k: int = 3) -> None:
    print(f"\nQUERY: {decision.query}")
    print("=" * 90)
    print(f"status: {decision.status}")
    print(f"reason: {decision.reason}")
    print(f"confidence: {decision.confidence:.3f}")
    print(f"multi_source: {decision.multi_source}")
    if decision.temporal_context:
        print(f"temporal_context: {decision.temporal_context}")
    print("top_results:")
    for rank, result in enumerate(decision.top_results[:display_top_k], start=1):
        temporal = ""
        if result.get("temporal_context"):
            temporal = f" | {result['temporal_context'].get('year')}"
        print(f"- {rank}. {result['chunk_id']} | {result['file_path']} | score={result['score']:.3f}{temporal}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run answerability decisions for queries.")
    parser.add_argument("queries", nargs="*")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--chunks", type=Path, default=Path("data/phase_a/course_chunks.jsonl"))
    parser.add_argument("--cache-dir", type=Path, default=Path("backend/indexes"))
    args = parser.parse_args()

    queries = args.queries or [
        "What is convex hull?",
        "When is assignment 1 due?",
        "How is Materials Project data related to MACE?",
        "What is the cafeteria menu today?",
        "Tell me about models",
    ]

    retriever = HybridRetriever(chunks_path=args.chunks, cache_dir=args.cache_dir)
    gate = AnswerabilityGate()

    for query in queries:
        results = retriever.search(query, top_k=args.top_k)
        print_decision(gate.decide(query, results))


if __name__ == "__main__":
    main()
