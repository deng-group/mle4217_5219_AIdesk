#!/usr/bin/env python3
"""Phase C LLM-layer smoke evaluation.

The default provider is dry-run, so this evaluates the answer-generation
contract without requiring a real LLM call.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.answer_generator import AnswerGenerator, provider_from_name
from backend.app.prompt_builder import PromptBuilder
from backend.app.query_pipeline import QueryPipeline


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_text(result: dict) -> str:
    parts = []
    for item in result.get("evidence", []):
        parts.extend([item.get("chunk_id", ""), item.get("file_path", ""), item.get("content", "")])
    return "\n".join(parts).lower()


def evaluate_case(case: dict, result: dict) -> dict:
    checks = {
        "status": result["status"] == case["expected_status"],
        "llm_action": result["llm_action"] == case["expected_action"],
    }
    if "expected_temporal_context" in case:
        checks["temporal_context"] = result["temporal_context"] == case["expected_temporal_context"]
    if "expected_memory_persistence" in case:
        policy = result["prompt_package"]["answer_policy"]
        checks["memory_persistence"] = policy["memory_persistence"] == case["expected_memory_persistence"]
        checks["short_memory_included"] = bool(result["short_memory"])
    if "expected_citation_terms" in case:
        haystack = evidence_text(result)
        checks["citation_terms"] = any(term.lower() in haystack for term in case["expected_citation_terms"])

    return {
        "id": case["id"],
        "query": case["query"],
        "passed": all(checks.values()),
        "checks": checks,
        "result": result,
    }


def write_report(path: Path, evaluations: list[dict], provider: str) -> None:
    passed = sum(item["passed"] for item in evaluations)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Phase C LLM Smoke Report",
        "",
        f"- Generated: **{generated_at}**",
        f"- Provider: **{provider}**",
        f"- Cases: **{len(evaluations)}**",
        f"- Passed: **{passed} / {len(evaluations)}**",
        "",
        "| Result | ID | Status | Action | Temporal context | Evidence | Answer preview |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in evaluations:
        result = item["result"]
        mark = "PASS" if item["passed"] else "FAIL"
        evidence = "<br>".join(
            f"`{entry['chunk_id']}` `{entry['score']:.3f}`" for entry in result.get("evidence", [])[:3]
        )
        answer = result["answer"].replace("|", "\\|")
        if len(answer) > 180:
            answer = answer[:177] + "..."
        lines.append(
            f"| {mark} | `{item['id']}` | `{result['status']}` | `{result['llm_action']}` | "
            f"`{result['temporal_context']}` | {evidence} | {answer} |"
        )

    failed = [item for item in evaluations if not item["passed"]]
    if failed:
        lines.extend(["", "## Failed Checks", ""])
        for item in failed:
            lines.append(f"- `{item['id']}`: `{item['checks']}`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase C LLM-layer smoke tests.")
    parser.add_argument("--cases", type=Path, default=Path("test/llm_smoke_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("test/llm_smoke_report.md"))
    parser.add_argument("--history-dir", type=Path, default=Path("test/llm_smoke_reports"))
    parser.add_argument("--provider", choices=["dry_run", "openai", "gemini", "anthropic"], default="dry_run")
    parser.add_argument("--model", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-evidence", type=int, default=None)
    parser.add_argument("--evidence-threshold", type=float, default=0.60)
    args = parser.parse_args()

    generator = AnswerGenerator(
        pipeline=QueryPipeline(top_k=args.top_k),
        prompt_builder=PromptBuilder(
            max_evidence=args.max_evidence,
            evidence_score_threshold=args.evidence_threshold,
        ),
        provider=provider_from_name(args.provider, model=args.model),
    )

    evaluations = []
    for case in load_cases(args.cases):
        result = generator.answer(case["query"], short_memory=case.get("short_memory", []))
        evaluations.append(evaluate_case(case, result))

    write_report(args.output, evaluations, args.provider)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_output = args.history_dir / f"llm_smoke_report_{timestamp}.md"
    write_report(history_output, evaluations, args.provider)

    passed = sum(item["passed"] for item in evaluations)
    print(f"Phase C LLM smoke eval: {passed}/{len(evaluations)} passed")
    print(f"Report: {args.output}")
    print(f"Historical report: {history_output}")
    for item in evaluations:
        if not item["passed"]:
            print(f"FAIL {item['id']}: checks={item['checks']}")


if __name__ == "__main__":
    main()
