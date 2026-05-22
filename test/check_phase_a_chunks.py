#!/usr/bin/env python3
"""Sanity checks for Phase A course chunks and knowledge graph.

This script checks whether the Phase A outputs are reasonable enough to use as
the basis for embeddings and RAG in Phase B.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


DEFAULT_KEYWORDS = [
    "convex hull",
    "Materials Project",
    "molecular dynamics",
    "Monte Carlo",
    "descriptor",
    "MACE",
    "DFT",
    "pandas",
    "crystal structure",
    "high throughput",
]


def load_chunks(path: Path) -> list[dict]:
    chunks = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
    return chunks


def load_graph(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def source_course_files(course_root: Path, exclude: set[str]) -> set[str]:
    ignored_parts = {
        ".git",
        "_build",
        "ai_agent_widget",
        "mle4217_5219_book.egg-info",
        ".ipynb_checkpoints",
        "__pycache__",
    }
    files = set()
    for path in course_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".md", ".ipynb"}:
            continue
        if any(part in ignored_parts for part in path.parts):
            continue
        relative = str(path.relative_to(course_root))
        if relative in exclude:
            continue
        files.add(relative)
    return files


def check_required_fields(chunks: list[dict]) -> dict[str, list[str]]:
    required = {
        "chunk_id",
        "content",
        "token_estimate",
        "file_path",
        "file_type",
        "module",
        "section",
        "title",
        "headings",
        "concepts",
        "code_blocks",
    }
    missing = defaultdict(list)
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", "<missing chunk_id>")
        for field in required - set(chunk):
            missing[field].append(chunk_id)
    return dict(missing)


def check_duplicate_ids(chunks: list[dict]) -> list[str]:
    counts = Counter(chunk.get("chunk_id") for chunk in chunks)
    return sorted(chunk_id for chunk_id, count in counts.items() if count > 1)


def chunk_length_stats(chunks: list[dict]) -> dict:
    lengths = [int(chunk.get("token_estimate", 0) or 0) for chunk in chunks]
    return {
        "min": min(lengths) if lengths else 0,
        "max": max(lengths) if lengths else 0,
        "mean": round(mean(lengths), 1) if lengths else 0,
        "median": round(median(lengths), 1) if lengths else 0,
    }


def find_extreme_chunks(chunks: list[dict], short_threshold: int, long_threshold: int) -> tuple[list[dict], list[dict]]:
    short = [chunk for chunk in chunks if int(chunk.get("token_estimate", 0) or 0) < short_threshold]
    long = [chunk for chunk in chunks if int(chunk.get("token_estimate", 0) or 0) > long_threshold]
    return short, long


def graph_linkage(chunks: list[dict], graph: dict) -> dict:
    chunk_ids = {chunk["chunk_id"] for chunk in chunks if "chunk_id" in chunk}
    linked = set()
    node_chunk_counts = Counter()
    for node in graph.get("nodes", []):
        node_chunks = node.get("chunks", []) or []
        if node_chunks:
            node_chunk_counts[node.get("type", "unknown")] += len(node_chunks)
        linked.update(node_chunks)
    return {
        "chunk_count": len(chunk_ids),
        "linked_chunk_count": len(linked & chunk_ids),
        "unlinked_chunks": sorted(chunk_ids - linked),
        "missing_chunk_references": sorted(linked - chunk_ids),
        "node_chunk_counts": dict(node_chunk_counts),
    }


def coverage(chunks: list[dict], course_root: Path, exclude: set[str]) -> dict:
    source_files = source_course_files(course_root, exclude)
    chunk_files = {chunk.get("file_path") for chunk in chunks if chunk.get("file_path")}
    return {
        "source_file_count": len(source_files),
        "chunk_source_file_count": len(chunk_files),
        "missing_from_chunks": sorted(source_files - chunk_files),
        "chunk_files_not_in_current_repo": sorted(chunk_files - source_files),
    }


def keyword_hits(chunks: list[dict], keywords: list[str]) -> dict[str, list[dict]]:
    results = {}
    for keyword in keywords:
        pattern_text = re.escape(keyword).replace(r"\ ", r"[\s-]+")
        pattern = re.compile(pattern_text, flags=re.IGNORECASE)
        hits = []
        for chunk in chunks:
            if pattern.search(chunk.get("content", "")):
                hits.append(
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "module": chunk.get("module"),
                        "file_path": chunk.get("file_path"),
                        "title": chunk.get("title"),
                    }
                )
        results[keyword] = hits
    return results


def concept_quality(chunks: list[dict]) -> dict:
    concept_counts = Counter()
    noisy = []
    empty = []
    too_many = []
    for chunk in chunks:
        concepts = chunk.get("concepts", []) or []
        if not concepts:
            empty.append(chunk.get("chunk_id"))
        if len(concepts) > 20:
            too_many.append(chunk.get("chunk_id"))
        for concept in concepts:
            concept_counts[concept] += 1
            if len(concept) > 80 or "\n" in concept:
                noisy.append((chunk.get("chunk_id"), concept))
    return {
        "unique_concepts": len(concept_counts),
        "top_concepts": concept_counts.most_common(20),
        "chunks_without_concepts": empty,
        "chunks_with_more_than_20_concepts": too_many,
        "potentially_noisy_concepts": noisy[:50],
    }


def sample_chunks(chunks: list[dict], sample_size: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    if sample_size >= len(chunks):
        selected = chunks
    else:
        selected = rng.sample(chunks, sample_size)
    samples = []
    for chunk in selected:
        samples.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "module": chunk.get("module"),
                "file_path": chunk.get("file_path"),
                "token_estimate": chunk.get("token_estimate"),
                "title": chunk.get("title"),
                "concepts": (chunk.get("concepts", []) or [])[:10],
                "content_preview": chunk.get("content", "")[:900].replace("\n", " "),
            }
        )
    return samples


def format_chunk_list(chunks: list[dict], limit: int = 25) -> str:
    if not chunks:
        return "- None\n"
    lines = []
    for chunk in chunks[:limit]:
        lines.append(
            f"- `{chunk.get('chunk_id')}` | {chunk.get('token_estimate')} tokens | "
            f"`{chunk.get('file_path')}` | {chunk.get('title')}"
        )
    if len(chunks) > limit:
        lines.append(f"- ... {len(chunks) - limit} more")
    return "\n".join(lines) + "\n"


def format_string_list(items: list[str], limit: int = 50) -> str:
    if not items:
        return "- None\n"
    lines = [f"- `{item}`" for item in items[:limit]]
    if len(items) > limit:
        lines.append(f"- ... {len(items) - limit} more")
    return "\n".join(lines) + "\n"


def write_report(
    output_path: Path,
    chunks: list[dict],
    graph: dict,
    required_missing: dict[str, list[str]],
    duplicate_ids: list[str],
    length_stats: dict,
    short_chunks: list[dict],
    long_chunks: list[dict],
    linkage: dict,
    coverage_result: dict,
    keyword_result: dict[str, list[dict]],
    concept_result: dict,
    samples: list[dict],
    short_threshold: int,
    long_threshold: int,
) -> None:
    module_counts = Counter(chunk.get("module", "<missing>") for chunk in chunks)
    file_type_counts = Counter(chunk.get("file_type", "<missing>") for chunk in chunks)
    graph_metadata = graph.get("metadata", {})

    lines = [
        "# Phase A Chunk Quality Report",
        "",
        "## Summary",
        "",
        f"- Total chunks: **{len(chunks)}**",
        f"- Modules represented: **{len(module_counts)}**",
        f"- File types: **{dict(file_type_counts)}**",
        f"- Token estimate min / median / mean / max: **{length_stats['min']} / {length_stats['median']} / {length_stats['mean']} / {length_stats['max']}**",
        f"- Short chunks below {short_threshold} tokens: **{len(short_chunks)}**",
        f"- Long chunks above {long_threshold} tokens: **{len(long_chunks)}**",
        f"- Duplicate chunk IDs: **{len(duplicate_ids)}**",
        f"- Missing required fields: **{sum(len(v) for v in required_missing.values())}**",
        f"- Graph nodes: **{len(graph.get('nodes', []))}**",
        f"- Graph edges: **{len(graph.get('edges', []))}**",
        f"- Graph metadata: `{graph_metadata}`",
        f"- Chunks linked from graph: **{linkage['linked_chunk_count']} / {linkage['chunk_count']}**",
        f"- Unlinked chunks: **{len(linkage['unlinked_chunks'])}**",
        f"- Graph references missing chunks: **{len(linkage['missing_chunk_references'])}**",
        f"- Current course source files: **{coverage_result['source_file_count']}**",
        f"- Source files represented by chunks: **{coverage_result['chunk_source_file_count']}**",
        f"- Current source files missing from chunks: **{len(coverage_result['missing_from_chunks'])}**",
        f"- Chunk source files not in current repo: **{len(coverage_result['chunk_files_not_in_current_repo'])}**",
        f"- Unique extracted concepts: **{concept_result['unique_concepts']}**",
        "",
        "## Module Counts",
        "",
    ]

    for module, count in sorted(module_counts.items()):
        lines.append(f"- `{module}`: {count}")

    lines.extend(
        [
            "",
            "## Required Field Problems",
            "",
        ]
    )
    if required_missing:
        for field, ids in sorted(required_missing.items()):
            lines.append(f"- `{field}` missing in {len(ids)} chunks: {ids[:20]}")
    else:
        lines.append("- None")

    lines.extend(["", "## Duplicate Chunk IDs", "", format_string_list(duplicate_ids)])
    lines.extend([f"", f"## Short Chunks (< {short_threshold} tokens)", "", format_chunk_list(short_chunks)])
    lines.extend([f"", f"## Long Chunks (> {long_threshold} tokens)", "", format_chunk_list(long_chunks)])

    lines.extend(
        [
            "",
            "## Graph Linkage Problems",
            "",
            "### Unlinked Chunks",
            "",
            format_string_list(linkage["unlinked_chunks"]),
            "",
            "### Graph References Missing Chunks",
            "",
            format_string_list(linkage["missing_chunk_references"]),
            "",
            "## Course Coverage Drift",
            "",
            "### Current Source Files Missing From Chunks",
            "",
            format_string_list(coverage_result["missing_from_chunks"], limit=120),
            "",
            "### Chunk Source Files Not In Current Repo",
            "",
            format_string_list(coverage_result["chunk_files_not_in_current_repo"], limit=120),
            "",
            "## Keyword Sanity Check",
            "",
        ]
    )

    for keyword, hits in keyword_result.items():
        lines.append(f"### {keyword}")
        lines.append("")
        lines.append(f"- Hits: **{len(hits)}**")
        for hit in hits[:10]:
            lines.append(f"- `{hit['chunk_id']}` | `{hit['file_path']}` | {hit['title']}")
        if len(hits) > 10:
            lines.append(f"- ... {len(hits) - 10} more")
        lines.append("")

    lines.extend(
        [
            "## Concept Quality",
            "",
            f"- Chunks without concepts: **{len(concept_result['chunks_without_concepts'])}**",
            f"- Chunks with more than 20 concepts: **{len(concept_result['chunks_with_more_than_20_concepts'])}**",
            f"- Potentially noisy concepts shown: **{len(concept_result['potentially_noisy_concepts'])}**",
            "",
            "### Top Concepts",
            "",
        ]
    )

    for concept, count in concept_result["top_concepts"]:
        lines.append(f"- `{concept}`: {count}")

    lines.extend(["", "### Potentially Noisy Concepts", ""])
    if concept_result["potentially_noisy_concepts"]:
        for chunk_id, concept in concept_result["potentially_noisy_concepts"]:
            lines.append(f"- `{chunk_id}`: `{concept}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Random Sample For Manual Review", ""])
    for sample in samples:
        lines.extend(
            [
                f"### `{sample['chunk_id']}`",
                "",
                f"- Module: `{sample['module']}`",
                f"- File: `{sample['file_path']}`",
                f"- Tokens: `{sample['token_estimate']}`",
                f"- Title: {sample['title']}",
                f"- Concepts: `{sample['concepts']}`",
                "",
                sample["content_preview"],
                "",
            ]
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Phase A chunk quality.")
    parser.add_argument("--chunks", type=Path, default=Path("data/phase_a/course_chunks.jsonl"))
    parser.add_argument("--graph", type=Path, default=Path("data/phase_a/knowledge_graph.json"))
    parser.add_argument("--course-root", type=Path, default=Path("../MLE4217_5219_book"))
    parser.add_argument("--output", type=Path, default=Path("test/phase_a_chunk_quality_report.md"))
    parser.add_argument("--exclude", nargs="*", default=["AGENTS.md"])
    parser.add_argument("--sample-size", type=int, default=12)
    parser.add_argument("--seed", type=int, default=4275)
    parser.add_argument("--short-threshold", type=int, default=80)
    parser.add_argument("--long-threshold", type=int, default=450)
    args = parser.parse_args()

    chunks = load_chunks(args.chunks)
    graph = load_graph(args.graph)

    required_missing = check_required_fields(chunks)
    duplicate_ids = check_duplicate_ids(chunks)
    length_stats = chunk_length_stats(chunks)
    short_chunks, long_chunks = find_extreme_chunks(chunks, args.short_threshold, args.long_threshold)
    linkage = graph_linkage(chunks, graph)
    coverage_result = coverage(chunks, args.course_root, set(args.exclude))
    keyword_result = keyword_hits(chunks, DEFAULT_KEYWORDS)
    concept_result = concept_quality(chunks)
    samples = sample_chunks(chunks, args.sample_size, args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_report(
        output_path=args.output,
        chunks=chunks,
        graph=graph,
        required_missing=required_missing,
        duplicate_ids=duplicate_ids,
        length_stats=length_stats,
        short_chunks=short_chunks,
        long_chunks=long_chunks,
        linkage=linkage,
        coverage_result=coverage_result,
        keyword_result=keyword_result,
        concept_result=concept_result,
        samples=samples,
        short_threshold=args.short_threshold,
        long_threshold=args.long_threshold,
    )

    print("Phase A chunk quality check complete.")
    print(f"Report: {args.output}")
    print(f"Chunks: {len(chunks)}")
    print(f"Token min/median/mean/max: {length_stats['min']}/{length_stats['median']}/{length_stats['mean']}/{length_stats['max']}")
    print(f"Short chunks < {args.short_threshold}: {len(short_chunks)}")
    print(f"Long chunks > {args.long_threshold}: {len(long_chunks)}")
    print(f"Duplicate chunk IDs: {len(duplicate_ids)}")
    print(f"Missing required fields: {sum(len(v) for v in required_missing.values())}")
    print(f"Graph linked chunks: {linkage['linked_chunk_count']} / {linkage['chunk_count']}")
    print(f"Unlinked chunks: {len(linkage['unlinked_chunks'])}")
    print(f"Graph references missing chunks: {len(linkage['missing_chunk_references'])}")
    print(f"Current source files missing from chunks: {len(coverage_result['missing_from_chunks'])}")
    print(f"Chunk files not in current repo: {len(coverage_result['chunk_files_not_in_current_repo'])}")
    print("Keyword hits:")
    for keyword, hits in keyword_result.items():
        print(f"  {keyword}: {len(hits)}")


if __name__ == "__main__":
    main()
