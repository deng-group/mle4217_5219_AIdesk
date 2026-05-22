#!/usr/bin/env python3
"""Hybrid retrieval over Phase A course chunks.

Version 1 intentionally does not call an LLM. It answers the question:
"Given a student query, which course chunks should the future LLM read?"
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)?")

TERM_ALIASES = {
    "convexhull": "convex hull",
    "highthroughput": "high throughput",
    "materialsproject": "materials project",
    "machinelearning": "machine learning",
    "molecular dynamics": "molecular dynamics",
}

LOGISTICS_TERMS = {
    "assignment",
    "assignments",
    "before",
    "covered",
    "quiz",
    "quizzes",
    "exam",
    "final",
    "grading",
    "grade",
    "deadline",
    "deadlines",
    "schedule",
    "calendar",
    "syllabus",
    "lecture",
    "lectures",
    "midterm",
    "review",
    "topic",
    "topics",
    "week",
    "weeks",
    "when",
}

STOP_TERMS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "between",
    "do",
    "does",
    "for",
    "how",
    "in",
    "is",
    "it",
    "of",
    "or",
    "the",
    "to",
    "what",
    "when",
    "why",
}


def normalize_text(text: str) -> str:
    """Normalize query/document text for lexical search."""
    text = text.lower()
    text = text.replace("-", " ").replace("_", " ").replace("/", " ")
    for source, target in TERM_ALIASES.items():
        text = text.replace(source, target)
    return text


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(normalize_text(text))


def query_phrases(query: str) -> set[str]:
    """Extract useful 2-3 token phrases for exact phrase boosting."""
    terms = tokenize(query)
    phrases = set()
    for size in (2, 3):
        for idx in range(len(terms) - size + 1):
            window = terms[idx : idx + size]
            if all(term in STOP_TERMS for term in window):
                continue
            if window[0] in STOP_TERMS and window[-1] in STOP_TERMS:
                continue
            content_terms = [term for term in window if term not in STOP_TERMS]
            if len(content_terms) < 2:
                continue
            phrases.add(" ".join(window))
            phrases.add(" ".join(content_terms))
    return phrases


def load_chunks(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


@dataclass
class SearchResult:
    chunk_id: str
    file_path: str
    title: str
    module: str
    score: float
    bm25_score: float
    embedding_score: float
    time_sensitive: bool
    temporal_context: dict | None
    content: str
    content_preview: str


class BM25Index:
    """Small, dependency-free BM25 index."""

    def __init__(self, tokenized_docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.tokenized_docs = tokenized_docs
        self.k1 = k1
        self.b = b
        self.doc_lengths = np.array([len(doc) for doc in tokenized_docs], dtype=np.float32)
        self.avg_doc_length = float(np.mean(self.doc_lengths)) if len(self.doc_lengths) else 0.0
        self.term_freqs = [Counter(doc) for doc in tokenized_docs]
        self.doc_freqs = Counter()
        for doc in tokenized_docs:
            self.doc_freqs.update(set(doc))
        self.num_docs = len(tokenized_docs)
        self.idf = {
            term: math.log(1 + (self.num_docs - df + 0.5) / (df + 0.5))
            for term, df in self.doc_freqs.items()
        }

    def search(self, query: str) -> np.ndarray:
        query_terms = [term for term in tokenize(query) if term not in STOP_TERMS]
        scores = np.zeros(self.num_docs, dtype=np.float32)
        if not query_terms or self.num_docs == 0:
            return scores

        for term in query_terms:
            idf = self.idf.get(term)
            if idf is None:
                continue
            for idx, freqs in enumerate(self.term_freqs):
                tf = freqs.get(term, 0)
                if tf == 0:
                    continue
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * self.doc_lengths[idx] / max(self.avg_doc_length, 1)
                )
                scores[idx] += idf * (tf * (self.k1 + 1)) / denominator

        return scores


class EmbeddingIndex:
    """Sentence-transformers embedding index with a TF-IDF fallback."""

    def __init__(self, chunks: list[dict], cache_dir: Path, model_name: str):
        self.chunks = chunks
        self.cache_dir = cache_dir
        self.model_name = model_name
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.vectorizer = None
        self.chunk_embeddings = None
        self.backend = "sentence-transformers"
        self._load_or_build()

    @property
    def cache_path(self) -> Path:
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.model_name)
        return self.cache_dir / f"embeddings_{safe_name}.npz"

    def _load_or_build(self) -> None:
        chunk_ids = np.array([chunk["chunk_id"] for chunk in self.chunks])

        if self.cache_path.exists():
            cached = np.load(self.cache_path, allow_pickle=True)
            cached_ids = cached["chunk_ids"]
            if list(cached_ids) == list(chunk_ids):
                self.chunk_embeddings = cached["embeddings"].astype(np.float32)
                self.backend = str(cached["backend"])
                if self.backend == "sentence-transformers":
                    self.model = self._load_sentence_transformer()
                else:
                    self._build_tfidf()
                return

        try:
            self.model = self._load_sentence_transformer()
            texts = [chunk["content"] for chunk in self.chunks]
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=True,
                batch_size=32,
            )
            self.chunk_embeddings = np.asarray(embeddings, dtype=np.float32)
            self.backend = "sentence-transformers"
        except Exception as exc:
            print(f"Warning: sentence-transformers unavailable ({exc}). Falling back to TF-IDF.")
            self._build_tfidf()
            self.backend = "tfidf"

        np.savez_compressed(
            self.cache_path,
            chunk_ids=chunk_ids,
            embeddings=self.chunk_embeddings,
            backend=np.array(self.backend),
        )

    def _load_sentence_transformer(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    def _build_tfidf(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
            preprocessor=normalize_text,
        )
        matrix = self.vectorizer.fit_transform([chunk["content"] for chunk in self.chunks])
        self.chunk_embeddings = normalize(matrix).astype(np.float32)

    def search(self, query: str) -> np.ndarray:
        if self.backend == "sentence-transformers":
            query_embedding = self.model.encode([query], normalize_embeddings=True)[0].astype(np.float32)
            return np.asarray(self.chunk_embeddings @ query_embedding, dtype=np.float32)

        from sklearn.preprocessing import normalize

        query_vector = normalize(self.vectorizer.transform([query])).astype(np.float32)
        return np.asarray((self.chunk_embeddings @ query_vector.T).toarray()).ravel().astype(np.float32)


class HybridRetriever:
    """BM25 + embedding retrieval with simple score fusion and metadata boosts."""

    def __init__(
        self,
        chunks_path: Path = Path("data/phase_a/course_chunks.jsonl"),
        cache_dir: Path = Path("backend/indexes"),
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.chunks = load_chunks(chunks_path)
        self.bm25 = BM25Index([tokenize(chunk["content"]) for chunk in self.chunks])
        self.embedding = EmbeddingIndex(self.chunks, cache_dir, model_name)

    def search(self, query: str, top_k: int = 5, candidate_k: int = 30) -> list[SearchResult]:
        bm25_scores = self.bm25.search(query)
        embedding_scores = self.embedding.search(query)

        bm25_norm = self._minmax(bm25_scores)
        embedding_norm = self._minmax(embedding_scores)
        fused = 0.45 * bm25_norm + 0.55 * embedding_norm

        query_tokens = set(tokenize(query))
        phrases = query_phrases(query)

        if query_tokens & LOGISTICS_TERMS:
            for idx, chunk in enumerate(self.chunks):
                if chunk.get("time_sensitive") or chunk.get("file_path") in {"syllabus.md", "calendar.md"}:
                    fused[idx] += 0.25

        wants_figures = bool(query_tokens & {"figure", "figures", "plot", "plots", "image", "images"})
        wants_comparison = bool(query_tokens & {"difference", "differences", "compare", "comparison", "versus", "vs"})
        for idx, chunk in enumerate(self.chunks):
            searchable = normalize_text(
                " ".join(
                    [
                        chunk.get("title", ""),
                        chunk.get("file_path", ""),
                        chunk.get("content", ""),
                    ]
                )
            )
            title_and_path = normalize_text(f"{chunk.get('title', '')} {chunk.get('file_path', '')}")
            for phrase in phrases:
                if phrase in searchable:
                    fused[idx] += 0.10
                if phrase in title_and_path:
                    fused[idx] += 0.18
            if wants_comparison and "comparison" in searchable:
                fused[idx] += 0.14
            if chunk.get("module") == "figures" and not wants_figures:
                fused[idx] *= 0.82

        sorted_indices = list(np.argsort(fused)[::-1][:candidate_k])
        selected_indices = sorted_indices[:top_k]

        if query_tokens & LOGISTICS_TERMS:
            has_temporal_result = any(
                self.chunks[int(idx)].get("time_sensitive") for idx in selected_indices
            )
            if not has_temporal_result:
                temporal_indices = [
                    idx for idx in sorted_indices
                    if self.chunks[int(idx)].get("time_sensitive")
                ]
                if temporal_indices:
                    selected_indices = selected_indices[: max(top_k - 1, 0)] + [temporal_indices[0]]

        results = []
        for idx in selected_indices:
            chunk = self.chunks[int(idx)]
            results.append(
                SearchResult(
                    chunk_id=chunk["chunk_id"],
                    file_path=chunk["file_path"],
                    title=chunk.get("title", ""),
                    module=chunk.get("module", ""),
                    score=float(fused[idx]),
                    bm25_score=float(bm25_scores[idx]),
                    embedding_score=float(embedding_scores[idx]),
                    time_sensitive=bool(chunk.get("time_sensitive", False)),
                    temporal_context=chunk.get("temporal_context"),
                    content=chunk["content"],
                    content_preview=self._preview(chunk["content"]),
                )
            )
        return results

    @staticmethod
    def _minmax(scores: np.ndarray) -> np.ndarray:
        if len(scores) == 0:
            return scores
        low = float(np.min(scores))
        high = float(np.max(scores))
        if math.isclose(high, low):
            return np.zeros_like(scores, dtype=np.float32)
        return (scores - low) / (high - low)

    @staticmethod
    def _preview(text: str, max_chars: int = 360) -> str:
        preview = re.sub(r"\s+", " ", text).strip()
        if len(preview) <= max_chars:
            return preview
        return preview[: max_chars - 1].rstrip() + "..."


def print_results(query: str, results: Iterable[SearchResult]) -> None:
    print(f"\nQUERY: {query}")
    print("=" * 90)
    for rank, result in enumerate(results, start=1):
        time_context = ""
        if result.temporal_context:
            time_context = f" | {result.temporal_context.get('year')}"
        print(
            f"{rank}. {result.chunk_id} | {result.file_path} | score={result.score:.3f} "
            f"| bm25={result.bm25_score:.3f} | emb={result.embedding_score:.3f}{time_context}"
        )
        print(f"   {result.content_preview}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run hybrid retrieval over course chunks.")
    parser.add_argument("queries", nargs="*", help="Queries to test.")
    parser.add_argument("--chunks", type=Path, default=Path("data/phase_a/course_chunks.jsonl"))
    parser.add_argument("--cache-dir", type=Path, default=Path("backend/indexes"))
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    queries = args.queries or [
        "What is convex hull?",
        "How is Materials Project used?",
        "What is the difference between molecular dynamics and Monte Carlo?",
        "When is assignment 1 due?",
        "convexhull",
    ]

    retriever = HybridRetriever(args.chunks, args.cache_dir, args.model)
    print(f"Embedding backend: {retriever.embedding.backend}")
    print(f"Chunks loaded: {len(retriever.chunks)}")

    for query in queries:
        print_results(query, retriever.search(query, top_k=args.top_k))


if __name__ == "__main__":
    main()
