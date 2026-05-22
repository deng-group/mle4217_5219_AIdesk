#!/usr/bin/env python3
"""Evaluate retrieval quality against a small hand-written question set."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.retriever import HybridRetriever, SearchResult, normalize_text


def load_eval_set(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def result_text(result: SearchResult) -> str:
    return normalize_text(" ".join([result.file_path, result.title, result.content_preview]))


def has_expected_file(results: list[SearchResult], expected_files: list[str]) -> bool:
    if not expected_files:
        return True
    result_files = {result.file_path for result in results}
    return any(file_path in result_files for file_path in expected_files)


def has_expected_terms(results: list[SearchResult], expected_terms: list[str]) -> bool:
    if not expected_terms:
        return True
    combined = "\n".join(result_text(result) for result in results)
    return any(normalize_text(term) in combined for term in expected_terms)


def has_temporal_context(results: list[SearchResult], expected_context: str | None) -> bool:
    if not expected_context:
        return True
    return any(
        result.temporal_context and result.temporal_context.get("year") == expected_context
        for result in results
    )


def is_weak_result(results: list[SearchResult], threshold: float) -> bool:
    if not results:
        return True
    top = results[0]
    return top.score < threshold or (top.bm25_score <= 0.01 and top.embedding_score < 0.22)


def evaluate_case(case: dict, results: list[SearchResult], weak_threshold: float) -> dict:
    expected_files = case.get("expected_files", [])
    expected_terms = case.get("expected_terms", [])
    expected_context = case.get("expected_temporal_context")
    should_be_weak = bool(case.get("should_be_weak", False))
    xfail = bool(case.get("xfail", False))

    checks = {
        "expected_file_hit": has_expected_file(results, expected_files),
        "expected_term_hit": has_expected_terms(results, expected_terms),
        "temporal_context_hit": has_temporal_context(results, expected_context),
        "weak_result_hit": is_weak_result(results, weak_threshold) if should_be_weak else True,
    }
    raw_passed = all(checks.values())
    passed = raw_passed or xfail

    return {
        "id": case["id"],
        "query": case["query"],
        "passed": passed,
        "raw_passed": raw_passed,
        "xfail": xfail,
        "checks": checks,
        "top_results": [asdict(result) for result in results],
        "notes": case.get("notes", ""),
    }


def write_report(path: Path, evaluations: list[dict], top_k: int, weak_threshold: float, display_top_k: int) -> None:
    passed = sum(1 for item in evaluations if item["passed"])
    xfailed = sum(1 for item in evaluations if item["xfail"] and not item["raw_passed"])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Retrieval Evaluation Report",
        "",
        f"- Generated: **{generated_at}**",
        f"- Cases: **{len(evaluations)}**",
        f"- Passed: **{passed} / {len(evaluations)}**",
        f"- Expected failures: **{xfailed}**",
        f"- Top-k evaluated: **{top_k}**",
        f"- Results shown per case: **{display_top_k}**",
        "",
    ]

    for item in evaluations:
        if item["xfail"] and not item["raw_passed"]:
            status = "XFAIL"
        else:
            status = "PASS" if item["passed"] else "FAIL"
        lines.extend(
            [
                f"## {status}: `{item['id']}`",
                "",
                f"Query: `{item['query']}`",
                "",
                f"Notes: {item['notes']}",
                "",
                "Top results:",
            ]
        )
        for rank, result in enumerate(item["top_results"][:display_top_k], start=1):
            temporal = ""
            if result.get("temporal_context"):
                temporal = f" | {result['temporal_context'].get('year')}"
            lines.append(
                f"- {rank}. `{result['chunk_id']}` | `{result['file_path']}` "
                f"| score={result['score']:.3f}{temporal}"
            )
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the Phase B1 retriever.")
    parser.add_argument("--eval-set", type=Path, default=Path("backend/evals/retrieval_eval_set.json"))
    parser.add_argument("--output", type=Path, default=Path("test/retrieval_eval_report.md"))
    parser.add_argument("--history-dir", type=Path, default=Path("test/retrieval_eval_reports"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--display-top-k", type=int, default=3)
    parser.add_argument("--weak-threshold", type=float, default=0.25)
    parser.add_argument("--chunks", type=Path, default=Path("data/phase_a/course_chunks.jsonl"))
    parser.add_argument("--cache-dir", type=Path, default=Path("backend/indexes"))
    args = parser.parse_args()

    cases = load_eval_set(args.eval_set)
    retriever = HybridRetriever(chunks_path=args.chunks, cache_dir=args.cache_dir)

    evaluations = []
    for case in cases:
        results = retriever.search(case["query"], top_k=args.top_k)
        evaluations.append(evaluate_case(case, results, args.weak_threshold))

    write_report(args.output, evaluations, args.top_k, args.weak_threshold, args.display_top_k)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_output = args.history_dir / f"retrieval_eval_report_{timestamp}.md"
    write_report(history_output, evaluations, args.top_k, args.weak_threshold, args.display_top_k)

    passed = sum(1 for item in evaluations if item["passed"])
    print(f"Retrieval eval: {passed}/{len(evaluations)} passed")
    print(f"Report: {args.output}")
    print(f"Historical report: {history_output}")
    for item in evaluations:
        if not item["passed"]:
            top = item["top_results"][0] if item["top_results"] else None
            top_desc = f"{top['chunk_id']} ({top['file_path']})" if top else "no results"
            print(f"FAIL {item['id']}: top={top_desc} checks={item['checks']}")


if __name__ == "__main__":
    main()
