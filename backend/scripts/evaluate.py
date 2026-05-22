#!/usr/bin/env python3
"""Unified retrieval + answerability evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.answerability import AnswerabilityGate
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


def evaluate_case(case: dict, results: list[SearchResult], decision) -> dict:
    checks = {
        "status": decision.status == case["expected_status"],
        "expected_file": has_expected_file(results, case.get("expected_files", [])),
        "expected_terms": has_expected_terms(results, case.get("expected_terms", [])),
    }
    if "expected_temporal_context" in case:
        checks["temporal_context"] = decision.temporal_context == case["expected_temporal_context"]
    if "expected_multi_source" in case:
        checks["multi_source"] = decision.multi_source == case["expected_multi_source"]

    return {
        "id": case["id"],
        "query": case["query"],
        "expected_status": case["expected_status"],
        "expected_files": case.get("expected_files", []),
        "passed": all(checks.values()),
        "checks": checks,
        "notes": case.get("notes", ""),
        "decision": asdict(decision),
    }


def top_evidence(decision: dict, expected_files: list[str], limit: int = 3) -> str:
    selected = select_evidence_for_display(decision["top_results"], expected_files, limit)
    parts = []
    for result in selected:
        temporal = ""
        if result.get("temporal_context"):
            temporal = f" ({result['temporal_context'].get('year')})"
        parts.append(f"`{result['file_path']}` `{result['score']:.3f}`{temporal}")
    return "<br>".join(parts)


def select_evidence_for_display(results: list[dict], expected_files: list[str], limit: int) -> list[dict]:
    selected = []
    seen_chunks = set()

    def add(result: dict) -> None:
        if len(selected) >= limit:
            return
        if result["chunk_id"] in seen_chunks:
            return
        selected.append(result)
        seen_chunks.add(result["chunk_id"])

    if results:
        add(results[0])

    for expected_file in expected_files:
        for result in results:
            if result["file_path"] == expected_file:
                add(result)
                break

    if not any(result.get("temporal_context") for result in selected):
        for result in results:
            if result.get("temporal_context"):
                add(result)
                break

    for result in results:
        add(result)
        if len(selected) >= limit:
            break

    return selected


def write_report(path: Path, evaluations: list[dict], gate: AnswerabilityGate, display_top_k: int) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passed = sum(1 for item in evaluations if item["passed"])
    statuses = ["answerable", "needs_time_context", "needs_clarification", "weak_evidence", "out_of_scope"]

    lines = [
        "# Unified Evaluation Report",
        "",
        f"- Generated: **{generated_at}**",
        f"- Cases: **{len(evaluations)}**",
        f"- Passed: **{passed} / {len(evaluations)}**",
        f"- Results shown per case: **{display_top_k}**",
        "",
        "## Thresholds And Rules",
        "",
        "| Parameter | Value | Meaning |",
        "| --- | ---: | --- |",
        f"| `strong_score` | `{gate.strong_score:.2f}` | Reference threshold for strong retrieved evidence. |",
        f"| `weak_score` | `{gate.weak_score:.2f}` | Top score below this becomes `weak_evidence`. |",
        f"| `min_embedding_score` | `{gate.min_embedding_score:.2f}` | If BM25 is near zero and embedding is below this, evidence is weak. |",
        "| Multi-source closeness ratio | `0.72` | Results within 72% of the top score are considered close enough for multi-source detection. |",
        "| Logistics temporal boost | `+0.25` | Applied to `syllabus.md` / `calendar.md` for logistics questions. |",
        "",
        "Course-offering questions about schedule, grading, assignments, quizzes, exams, weeks, or reviews should carry **AY2025/2026 Semester 2** when using current syllabus/calendar evidence.",
        "",
    ]

    for status in statuses:
        group = [item for item in evaluations if item["decision"]["status"] == status]
        if not group:
            continue
        lines.extend(
            [
                f"## {status}",
                "",
                "| Result | ID | Question | Score | Multi-source | Top evidence |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for item in group:
            mark = "PASS" if item["passed"] else "FAIL"
            decision = item["decision"]
            question = item["query"].replace("|", "\\|")
            lines.append(
                f"| {mark} | `{item['id']}` | {question} | `{decision['confidence']:.3f}` | "
                f"`{decision['multi_source']}` | {top_evidence(decision, item.get('expected_files', []), display_top_k)} |"
            )
        lines.append("")

    failed = [item for item in evaluations if not item["passed"]]
    if failed:
        lines.extend(["## Failed Checks", ""])
        for item in failed:
            lines.append(f"- `{item['id']}`: `{item['checks']}`")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run unified retrieval + answerability evaluation.")
    parser.add_argument("--eval-set", type=Path, default=Path("test/eval_set.json"))
    parser.add_argument("--output", type=Path, default=Path("test/eval_report.md"))
    parser.add_argument("--history-dir", type=Path, default=Path("test/eval_reports"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--display-top-k", type=int, default=3)
    parser.add_argument("--chunks", type=Path, default=Path("data/phase_a/course_chunks.jsonl"))
    parser.add_argument("--cache-dir", type=Path, default=Path("backend/indexes"))
    args = parser.parse_args()

    cases = load_eval_set(args.eval_set)
    retriever = HybridRetriever(chunks_path=args.chunks, cache_dir=args.cache_dir)
    gate = AnswerabilityGate()

    evaluations = []
    for case in cases:
        results = retriever.search(case["query"], top_k=args.top_k)
        decision = gate.decide(case["query"], results)
        evaluations.append(evaluate_case(case, results, decision))

    write_report(args.output, evaluations, gate, args.display_top_k)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_output = args.history_dir / f"eval_report_{timestamp}.md"
    write_report(history_output, evaluations, gate, args.display_top_k)

    passed = sum(1 for item in evaluations if item["passed"])
    print(f"Unified eval: {passed}/{len(evaluations)} passed")
    print(f"Report: {args.output}")
    print(f"Historical report: {history_output}")
    for item in evaluations:
        if not item["passed"]:
            print(f"FAIL {item['id']}: decision={item['decision']['status']} checks={item['checks']}")


if __name__ == "__main__":
    main()
