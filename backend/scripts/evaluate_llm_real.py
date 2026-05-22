#!/usr/bin/env python3
"""Run real LLM answer-generation tests for manual review.

This script calls an external provider by default. For Gemini, it supports a
simple retry policy and model fallback for transient provider failures.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.answer_generator import AnswerGenerator, load_env_file, provider_from_name
from backend.app.prompt_builder import PromptBuilder
from backend.app.query_pipeline import QueryPipeline


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_generator(model: str, top_k: int, max_evidence: int | None, evidence_threshold: float) -> AnswerGenerator:
    return AnswerGenerator(
        pipeline=QueryPipeline(top_k=top_k),
        prompt_builder=PromptBuilder(
            max_evidence=max_evidence,
            evidence_score_threshold=evidence_threshold,
        ),
        provider=provider_from_name("gemini", model=model),
    )


def answer_with_retry(case: dict, args: argparse.Namespace) -> dict:
    models = [args.model]
    if args.fallback_model and args.fallback_model not in models:
        models.append(args.fallback_model)

    attempts = []
    last_error = None
    for model_idx, model in enumerate(models):
        retries = args.retries if model_idx == 0 else args.fallback_retries
        for attempt_idx in range(1, retries + 2):
            try:
                generator = build_generator(model, args.top_k, args.max_evidence, args.evidence_threshold)
                result = generator.answer(case["query"], short_memory=case.get("short_memory", []))
                result.pop("raw_response", None)
                result.pop("prompt_package", None)
                attempts.append(
                    {
                        "model": model,
                        "attempt": attempt_idx,
                        "ok": True,
                    }
                )
                return {
                    "case": case,
                    "ok": True,
                    "attempts": attempts,
                    "result": result,
                    "error": None,
                }
            except Exception as exc:
                last_error = exc
                attempts.append(
                    {
                        "model": model,
                        "attempt": attempt_idx,
                        "ok": False,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )
                has_more_attempts = attempt_idx <= retries
                has_fallback = model_idx + 1 < len(models)
                if has_more_attempts:
                    time.sleep(args.retry_delay)
                elif has_fallback:
                    time.sleep(args.retry_delay)

    return {
        "case": case,
        "ok": False,
        "attempts": attempts,
        "result": None,
        "error": {
            "type": type(last_error).__name__ if last_error else "UnknownError",
            "message": str(last_error) if last_error else "No result produced.",
        },
    }


def status_checks(case: dict, result: dict | None) -> dict:
    if not result:
        return {"llm_call": False}
    checks = {"llm_call": True}
    if "expected_status" in case:
        checks["status"] = result["status"] == case["expected_status"]
    if "expected_temporal_context" in case:
        checks["temporal_context"] = result["temporal_context"] == case["expected_temporal_context"]
    checks["has_answer"] = bool(result.get("answer", "").strip())
    checks["has_sources"] = bool(result.get("sources"))
    return checks


def compact_sources(result: dict | None) -> str:
    if not result:
        return ""
    sources = result.get("sources", [])[:3]
    return "<br>".join(f"`{item['title']}` `{item['file_path']}` `{item['score']:.3f}`" for item in sources)


def answer_block(item: dict) -> list[str]:
    case = item["case"]
    result = item["result"]
    lines = [
        f"### {case['id']}",
        "",
        f"- Category: `{case.get('category', '')}`",
        f"- Query: {case['query']}",
        f"- OK: `{item['ok']}`",
        f"- Checks: `{status_checks(case, result)}`",
        f"- Attempts: `{item['attempts']}`",
    ]
    if result:
        lines.extend(
            [
                f"- Status: `{result['status']}`",
                f"- Model: `{result['model']}`",
                f"- Temporal context: `{result['temporal_context']}`",
                "",
                "**Sources**",
                "",
                compact_sources(result) or "- None",
                "",
                "**Answer**",
                "",
                result["answer"],
            ]
        )
    else:
        lines.extend(["", "**Error**", "", f"`{item['error']}`"])
    lines.append("")
    return lines


def write_report(path: Path, results: list[dict], args: argparse.Namespace) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ok_count = sum(item["ok"] for item in results)
    lines = [
        "# Phase C Real LLM Report",
        "",
        f"- Generated: **{generated_at}**",
        f"- Primary model: **{args.model}**",
        f"- Fallback model: **{args.fallback_model}**",
        f"- Retries before fallback: **{args.retries}**",
        f"- Retry delay seconds: **{args.retry_delay}**",
        f"- Cases: **{len(results)}**",
        f"- LLM calls succeeded: **{ok_count} / {len(results)}**",
        "",
    ]
    lines.append("## Cases")
    lines.append("")
    for item in results:
        lines.extend(answer_block(item))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real Gemini LLM tests with retry and fallback.")
    parser.add_argument("--cases", type=Path, default=Path("test/llm_real_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("test/llm_real_report.md"))
    parser.add_argument("--history-dir", type=Path, default=Path("test/llm_real_reports"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--fallback-model", default="gemini-2.0-flash")
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--fallback-retries", type=int, default=0)
    parser.add_argument("--retry-delay", type=float, default=5.0)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-evidence", type=int, default=None)
    parser.add_argument("--evidence-threshold", type=float, default=0.60)
    args = parser.parse_args()

    load_env_file(args.env_file)
    results = [answer_with_retry(case, args) for case in load_cases(args.cases)]

    write_report(args.output, results, args)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_output = args.history_dir / f"llm_real_report_{timestamp}.md"
    write_report(history_output, results, args)

    ok_count = sum(item["ok"] for item in results)
    print(f"Phase C real LLM eval: {ok_count}/{len(results)} calls succeeded")
    print(f"Report: {args.output}")
    print(f"Historical report: {history_output}")
    for item in results:
        if not item["ok"]:
            print(f"FAIL {item['case']['id']}: {item['error']}")


if __name__ == "__main__":
    main()
