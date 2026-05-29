#!/usr/bin/env python3
"""Profile staged runtime with a fixed small question set."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.answerability import AnswerabilityGate
from backend.app.answer_generator import load_env_file, provider_from_name
from backend.app.prompt_builder import PromptBuilder
from backend.app.query_pipeline import NEXT_ACTIONS, QueryPipeline
from backend.app.retriever import HybridRetriever


DEFAULT_QUESTIONS = [
    "What is convex hull?",
    "How is Materials Project used in high-throughput screening?",
    "What is the difference between molecular dynamics and Monte Carlo?",
    "When is assignment 1 due?",
    "Tell me about models",
]


def timed_subprocess(args: list[str], cwd: Path) -> dict:
    start = time.perf_counter()
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = time.perf_counter() - start
    return {
        "args": args,
        "elapsed_s": elapsed,
        "returncode": completed.returncode,
        "output": completed.stdout,
    }


def count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def load_graph_counts(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("metadata", {})


def profile_phase_a(book_repo: Path, run_dir: Path) -> dict:
    chunks_path = run_dir / "course_chunks.jsonl"
    graph_path = run_dir / "knowledge_graph.json"

    extraction = timed_subprocess(
        [
            sys.executable,
            "scripts/phase_a/extract_content.py",
            "--repo",
            str(book_repo),
            "--output",
            str(chunks_path),
        ],
        REPO_ROOT,
    )
    if extraction["returncode"] != 0:
        return {
            "ok": False,
            "total_s": extraction["elapsed_s"],
            "extraction": extraction,
            "graph": None,
            "chunks_path": str(chunks_path),
            "graph_path": str(graph_path),
        }

    graph = timed_subprocess(
        [
            sys.executable,
            "scripts/phase_a/build_knowledge_graph.py",
            "--chunks",
            str(chunks_path),
            "--output",
            str(graph_path),
        ],
        REPO_ROOT,
    )

    return {
        "ok": graph["returncode"] == 0,
        "total_s": extraction["elapsed_s"] + graph["elapsed_s"],
        "extraction": extraction,
        "graph": graph,
        "chunks_path": str(chunks_path),
        "graph_path": str(graph_path),
        "chunk_count": count_jsonl(chunks_path) if chunks_path.exists() else None,
        "graph_counts": load_graph_counts(graph_path) if graph_path.exists() else {},
    }


def profile_phase_b(chunks_path: Path, cache_dir: Path, questions: list[str], top_k: int) -> dict:
    init_start = time.perf_counter()
    retriever = HybridRetriever(chunks_path=chunks_path, cache_dir=cache_dir)
    gate = AnswerabilityGate()
    init_s = time.perf_counter() - init_start

    cases = []
    pipeline_results = []
    for question in questions:
        retrieval_start = time.perf_counter()
        results = retriever.search(question, top_k=top_k)
        retrieval_s = time.perf_counter() - retrieval_start

        gate_start = time.perf_counter()
        decision = gate.decide(question, results)
        gate_s = time.perf_counter() - gate_start

        cases.append(
            {
                "question": question,
                "retrieval_s": retrieval_s,
                "answerability_s": gate_s,
                "total_s": retrieval_s + gate_s,
                "status": decision.status,
                "confidence": decision.confidence,
                "top_file": results[0].file_path if results else None,
                "top_score": results[0].score if results else None,
            }
        )
        pipeline_results.append(
            {
                "query": question,
                "retrieval_query": question,
                "status": decision.status,
                "next_action": NEXT_ACTIONS.get(decision.status, "inspect_manually"),
                "reason": decision.reason,
                "confidence": decision.confidence,
                "needs_temporal_context": decision.needs_temporal_context,
                "temporal_context": decision.temporal_context,
                "multi_source": decision.multi_source,
                "evidence": [
                    {
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
                    for result in results
                ],
            }
        )

    query_times = [case["total_s"] for case in cases]
    return {
        "ok": True,
        "total_s": init_s + sum(query_times),
        "init_s": init_s,
        "embedding_backend": retriever.embedding.backend,
        "chunk_count": len(retriever.chunks),
        "questions": cases,
        "mean_query_s": statistics.mean(query_times) if query_times else 0.0,
        "median_query_s": statistics.median(query_times) if query_times else 0.0,
        "max_query_s": max(query_times) if query_times else 0.0,
        "pipeline_results": pipeline_results,
    }


def default_provider_name() -> str:
    import os

    if os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "dry_run"


def default_model_name(provider: str) -> str | None:
    import os

    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_MODEL")
    if provider == "gemini":
        return os.environ.get("GEMINI_MODEL")
    if provider == "openai":
        return os.environ.get("OPENAI_MODEL")
    return None


def profile_phase_c(pipeline_results: list[dict], provider_name: str, model: str | None) -> dict:
    builder = PromptBuilder(evidence_score_threshold=0.60)
    provider = provider_from_name(provider_name, model=model)
    init_s = 0.0
    cases = []

    for pipeline_result in pipeline_results:
        prompt_start = time.perf_counter()
        prompt_package = builder.build(pipeline_result)
        prompt_s = time.perf_counter() - prompt_start

        provider_start = time.perf_counter()
        try:
            provider_result = provider.generate(prompt_package)
            ok = True
            error = None
        except Exception as exc:
            provider_result = {"provider": provider_name, "model": model, "answer": "", "citations": [], "raw_response": None}
            ok = False
            error = f"{type(exc).__name__}: {exc}"
        provider_s = time.perf_counter() - provider_start

        cases.append(
            {
                "question": pipeline_result["query"],
                "prompt_s": prompt_s,
                "provider_s": provider_s,
                "total_s": prompt_s + provider_s,
                "ok": ok,
                "error": error,
                "status": pipeline_result["status"],
                "provider": provider_result["provider"],
                "model": provider_result["model"],
                "answer_chars": len(provider_result.get("answer") or ""),
            }
        )

    case_times = [case["total_s"] for case in cases]
    return {
        "ok": all(case["ok"] for case in cases),
        "provider": provider_name,
        "model": model,
        "init_s": init_s,
        "total_s": init_s + sum(case_times),
        "questions": cases,
        "mean_query_s": statistics.mean(case_times) if case_times else 0.0,
        "median_query_s": statistics.median(case_times) if case_times else 0.0,
        "max_query_s": max(case_times) if case_times else 0.0,
    }


def profile_phase_d(questions: list[str]) -> dict:
    """Profile the Flask API route with the currently configured provider/model."""
    from web_app.app import app

    init_start = time.perf_counter()
    client = app.test_client()
    init_s = time.perf_counter() - init_start

    cases = []
    for question in questions:
        start = time.perf_counter()
        response = client.post(
            "/api/answer",
            json={
                "query": question,
                "short_memory": [],
            },
        )
        elapsed = time.perf_counter() - start
        payload = response.get_json(silent=True) or {}
        cases.append(
            {
                "question": question,
                "http_status": response.status_code,
                "ok": bool(payload.get("ok")),
                "total_s": elapsed,
                "status": payload.get("status"),
                "provider": payload.get("provider"),
                "model": payload.get("model"),
                "message": payload.get("message"),
            }
        )

    case_times = [case["total_s"] for case in cases]
    return {
        "ok": all(case["ok"] for case in cases),
        "init_s": init_s,
        "total_s": init_s + sum(case_times),
        "questions": cases,
        "mean_query_s": statistics.mean(case_times) if case_times else 0.0,
        "median_query_s": statistics.median(case_times) if case_times else 0.0,
        "max_query_s": max(case_times) if case_times else 0.0,
        "note": "Uses Flask test client against `/api/answer` with the current `.env` provider/model, matching the book widget request path.",
    }


def fmt(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    return f"{seconds:.3f}s"


def tail(text: str, max_lines: int = 12) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return "\n".join(lines[-max_lines:])


def write_report(path: Path, run_dir: Path, phase_a: dict | None, phase_b: dict, phase_c: dict, phase_d: dict) -> None:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Phase Runtime Profile",
        "",
        f"- Generated: **{generated}**",
        f"- Run directory: `{run_dir}`",
        "- Scope: Phase B, Phase C, and Phase D on 5 fixed questions.",
        "- Phase A is treated as completed and is not rerun by default.",
        "",
        "## Summary",
        "",
        "| Phase | Total | Main Components |",
        "| --- | ---: | --- |",
    (
            f"| Phase B | {fmt(phase_b.get('total_s'))} | "
            f"retriever_init={fmt(phase_b.get('init_s'))}, "
            f"5_queries={fmt(sum(item['total_s'] for item in phase_b.get('questions', [])))} |"
        ),
        (
            f"| Phase C | {fmt(phase_c.get('total_s'))} | "
            f"provider={phase_c.get('provider')} model={phase_c.get('model')}, "
            f"prompt_build={fmt(sum(item['prompt_s'] for item in phase_c.get('questions', [])))}, "
            f"model_calls={fmt(sum(item['provider_s'] for item in phase_c.get('questions', [])))} |"
        ),
        (
            f"| Phase D | {fmt(phase_d.get('total_s'))} | "
            f"api_init={fmt(phase_d.get('init_s'))}, "
            f"5_api_posts={fmt(sum(item['total_s'] for item in phase_d.get('questions', [])))} |"
        ),
        "| Phase E | Not profiled | Deployment/pilot workflow has no local executable phase in this repo. |",
        "",
    ]

    if phase_a:
        graph_counts = phase_a.get("graph_counts") or {}
        lines.extend(
            [
                "",
                "## Phase A Reference",
                "",
                f"- Total: **{fmt(phase_a.get('total_s'))}**",
                f"- Chunks: **{phase_a.get('chunk_count', '-')}**",
            ]
        )
        if graph_counts:
            lines.append(
                f"- Graph nodes/edges: **{graph_counts.get('num_nodes', '-')} / {graph_counts.get('num_edges', '-')}**"
            )

    lines.extend(
        [
            "",
            "## Phase B Details",
            "",
            f"- Chunks loaded: **{phase_b.get('chunk_count', '-')}**",
            f"- Embedding backend: **{phase_b.get('embedding_backend', '-')}**",
            f"- Mean query time: **{fmt(phase_b.get('mean_query_s'))}**",
            f"- Median query time: **{fmt(phase_b.get('median_query_s'))}**",
            f"- Slowest query time: **{fmt(phase_b.get('max_query_s'))}**",
            "",
            "| Question | Retrieval | Answerability | Total | Status | Top Evidence |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for item in phase_b.get("questions", []):
        question = item["question"].replace("|", "\\|")
        top_file = item["top_file"] or "-"
        top_score = f"{item['top_score']:.3f}" if item["top_score"] is not None else "-"
        lines.append(
            f"| {question} | {fmt(item['retrieval_s'])} | {fmt(item['answerability_s'])} | "
            f"{fmt(item['total_s'])} | `{item['status']}` | `{top_file}` `{top_score}` |"
        )

    lines.extend(
        [
            "",
            "## Phase C Details",
            "",
            f"- Provider/model: **{phase_c.get('provider')} / {phase_c.get('model')}**",
            f"- Mean question time: **{fmt(phase_c.get('mean_query_s'))}**",
            f"- Median question time: **{fmt(phase_c.get('median_query_s'))}**",
            f"- Slowest question time: **{fmt(phase_c.get('max_query_s'))}**",
            "",
            "| Question | Prompt Build | Model Call | Total | OK | Status | Answer Chars |",
            "| --- | ---: | ---: | ---: | --- | --- | ---: |",
        ]
    )
    for item in phase_c.get("questions", []):
        question = item["question"].replace("|", "\\|")
        ok = "yes" if item["ok"] else "no"
        lines.append(
            f"| {question} | {fmt(item['prompt_s'])} | {fmt(item['provider_s'])} | "
            f"{fmt(item['total_s'])} | {ok} | `{item['status']}` | {item['answer_chars']} |"
        )
    failed_c = [item for item in phase_c.get("questions", []) if not item["ok"]]
    if failed_c:
        lines.extend(["", "Phase C errors:", ""])
        for item in failed_c:
            lines.append(f"- `{item['question']}`: {item['error']}")

    lines.extend(
        [
            "",
            "## Phase D Details",
            "",
            f"- Mean API POST time: **{fmt(phase_d.get('mean_query_s'))}**",
            f"- Median API POST time: **{fmt(phase_d.get('median_query_s'))}**",
            f"- Slowest API POST time: **{fmt(phase_d.get('max_query_s'))}**",
            f"- Note: {phase_d.get('note')}",
            "",
            "| Question | API POST | HTTP | OK | Provider | Model | Status |",
            "| --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for item in phase_d.get("questions", []):
        question = item["question"].replace("|", "\\|")
        ok = "yes" if item["ok"] else "no"
        lines.append(
            f"| {question} | {fmt(item['total_s'])} | {item['http_status']} | {ok} | "
            f"`{item.get('provider')}` | `{item.get('model')}` | `{item['status']}` |"
        )

    lines.extend(["", "## Notes", ""])
    if phase_a and phase_a.get("extraction", {}).get("returncode") != 0:
        lines.extend(["Phase A extraction failed:", "", "```text", tail(phase_a["extraction"]["output"]), "```", ""])
    if phase_a and (phase_a.get("graph") or {}).get("returncode") not in {0, None}:
        lines.extend(["Phase A graph build failed:", "", "```text", tail(phase_a["graph"]["output"]), "```", ""])
    lines.append(
        "Phase B includes retriever initialization, which may include loading the sentence-transformers model and reading/building the embedding index cache."
    )
    lines.append("Phase C isolates prompt construction and configured model-provider latency using the Phase B outputs.")
    lines.append("Phase D measures the local `/api/answer` route with the current `.env` provider/model, so it includes route overhead, retriever setup, and real model latency.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile staged runtimes.")
    parser.add_argument("--book-repo", type=Path, default=Path("../MLE4217_5219_book"))
    parser.add_argument("--chunks", type=Path, default=Path("data/phase_a/course_chunks.jsonl"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output", type=Path, default=Path("test/phase_profile_report.md"))
    parser.add_argument("--run-root", type=Path, default=Path("test/profile_runs"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--include-phase-a", action="store_true", help="Rerun Phase A and include its detailed timing.")
    parser.add_argument("--phase-c-provider", choices=["dry_run", "openai", "gemini", "anthropic"], default=None)
    parser.add_argument("--phase-c-model", default=None)
    args = parser.parse_args()

    load_env_file(args.env_file)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.run_root / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    phase_a = profile_phase_a(args.book_repo, run_dir) if args.include_phase_a else None
    chunks_path = Path(phase_a["chunks_path"]) if phase_a and phase_a.get("ok") else args.chunks
    phase_b = profile_phase_b(chunks_path, run_dir / "phase_b_cache", DEFAULT_QUESTIONS, args.top_k)
    provider = args.phase_c_provider or default_provider_name()
    model = args.phase_c_model or default_model_name(provider)
    phase_c = profile_phase_c(phase_b["pipeline_results"], provider, model)
    phase_d = profile_phase_d(DEFAULT_QUESTIONS)
    write_report(args.output, run_dir, phase_a, phase_b, phase_c, phase_d)

    print(f"Profile report: {args.output}")
    print(f"Phase B: {fmt(phase_b.get('total_s'))}")
    print(f"Phase C: {fmt(phase_c.get('total_s'))}")
    print(f"Phase D: {fmt(phase_d.get('total_s'))}")


if __name__ == "__main__":
    main()
