#!/usr/bin/env python3
"""Evaluate the answerability gate against a small test set."""

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
from backend.app.retriever import HybridRetriever


def load_eval_set(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_case(case: dict, decision) -> dict:
    checks = {
        "status": decision.status == case["expected_status"],
    }
    if "expected_temporal_context" in case:
        checks["temporal_context"] = decision.temporal_context == case["expected_temporal_context"]
    if "expected_multi_source" in case:
        checks["multi_source"] = decision.multi_source == case["expected_multi_source"]

    return {
        "id": case["id"],
        "query": case["query"],
        "passed": all(checks.values()),
        "checks": checks,
        "decision": asdict(decision),
    }


def write_report(path: Path, evaluations: list[dict], display_top_k: int) -> None:
    passed = sum(1 for item in evaluations if item["passed"])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Answerability Evaluation Report",
        "",
        f"- Generated: **{generated_at}**",
        f"- Cases: **{len(evaluations)}**",
        f"- Passed: **{passed} / {len(evaluations)}**",
        f"- Results shown per case: **{display_top_k}**",
        "",
    ]

    for item in evaluations:
        decision = item["decision"]
        status = "PASS" if item["passed"] else "FAIL"
        temporal = f" | {decision['temporal_context']}" if decision.get("temporal_context") else ""
        lines.extend(
            [
                f"## {status}: `{item['id']}`",
                "",
                f"Query: `{item['query']}`",
                "",
                f"Decision: **{decision['status']}**{temporal}",
                "",
                f"Reason: {decision['reason']}",
                "",
                f"Confidence: `{decision['confidence']:.3f}`",
                "",
                f"Multi-source: `{decision['multi_source']}`",
                "",
                "Top results:",
            ]
        )
        display_results = select_display_results(decision["top_results"], display_top_k)
        for rank, result in enumerate(display_results, start=1):
            result_temporal = ""
            if result.get("temporal_context"):
                result_temporal = f" | {result['temporal_context'].get('year')}"
            lines.append(
                f"- {rank}. `{result['chunk_id']}` | `{result['file_path']}` "
                f"| score={result['score']:.3f}{result_temporal}"
            )
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def select_display_results(results: list[dict], display_top_k: int) -> list[dict]:
    """Prefer diverse files in compact reports while keeping rank order mostly intact."""
    selected = []
    seen_files = set()
    for result in results:
        if result["file_path"] in seen_files:
            continue
        selected.append(result)
        seen_files.add(result["file_path"])
        if len(selected) >= display_top_k:
            return selected
    for result in results:
        if result in selected:
            continue
        selected.append(result)
        if len(selected) >= display_top_k:
            return selected
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate answerability gate.")
    parser.add_argument("--eval-set", type=Path, default=Path("test/answerability_eval_set.json"))
    parser.add_argument("--output", type=Path, default=Path("test/answerability_eval_report.md"))
    parser.add_argument("--history-dir", type=Path, default=Path("test/answerability_eval_reports"))
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
        evaluations.append(evaluate_case(case, gate.decide(case["query"], results)))

    write_report(args.output, evaluations, args.display_top_k)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_output = args.history_dir / f"answerability_eval_report_{timestamp}.md"
    write_report(history_output, evaluations, args.display_top_k)

    passed = sum(1 for item in evaluations if item["passed"])
    print(f"Answerability eval: {passed}/{len(evaluations)} passed")
    print(f"Report: {args.output}")
    print(f"Historical report: {history_output}")
    for item in evaluations:
        if not item["passed"]:
            decision = item["decision"]
            print(f"FAIL {item['id']}: decision={decision['status']} checks={item['checks']}")


if __name__ == "__main__":
    main()
