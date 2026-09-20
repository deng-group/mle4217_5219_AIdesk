#!/usr/bin/env python3
"""Validate structural and grounding invariants of the Nexus graph."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH = REPO_ROOT / "nexus/data/course_graph.json"


def validate(graph: dict) -> list[str]:
    errors = []
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_ids = [node.get("id") for node in nodes]
    edge_ids = [edge.get("id") for edge in edges]
    known_nodes = set(node_ids)

    duplicate_nodes = [value for value, count in Counter(node_ids).items() if count > 1]
    duplicate_edges = [value for value, count in Counter(edge_ids).items() if count > 1]
    if duplicate_nodes:
        errors.append(f"Duplicate node IDs: {duplicate_nodes[:10]}")
    if duplicate_edges:
        errors.append(f"Duplicate edge IDs: {duplicate_edges[:10]}")

    for edge in edges:
        if edge.get("source") not in known_nodes:
            errors.append(f"Unknown edge source: {edge.get('id')} -> {edge.get('source')}")
        if edge.get("target") not in known_nodes:
            errors.append(f"Unknown edge target: {edge.get('id')} -> {edge.get('target')}")
        if edge.get("source") == edge.get("target"):
            errors.append(f"Self-edge: {edge.get('id')}")
        if not edge.get("evidence"):
            errors.append(f"Ungrounded edge: {edge.get('id')}")

    incident = Counter()
    for edge in edges:
        incident[edge.get("source")] += 1
        incident[edge.get("target")] += 1
    for node in nodes:
        if node.get("type") == "keyword" and not incident[node["id"]]:
            errors.append(f"Orphan keyword: {node['id']}")
        if node.get("type") in {"chapter", "topic", "keyword"} and not node.get("chunk_ids"):
            errors.append(f"Node has no course chunks: {node['id']}")

    primary_chapters = [
        node for node in nodes if node.get("type") == "chapter" and node.get("visibility") == "primary"
    ]
    if len(primary_chapters) < 10:
        errors.append(f"Expected at least 10 primary chapters, found {len(primary_chapters)}")
    if graph.get("stats", {}).get("cross_chapter_topic_bridges", 0) < 5:
        errors.append("Expected at least 5 cross-chapter topic bridges")
    forbidden_semantic_fields = {"predicate", "review_status"}
    for edge in edges:
        if forbidden_semantic_fields & edge.keys():
            errors.append(f"Relationship assigns semantic meaning: {edge.get('id')}")

    related_pairs = {
        frozenset((edge.get("source"), edge.get("target")))
        for edge in edges
        if edge.get("type") == "related"
    }
    expected_pairs = [
        {"keyword:materials-project", "keyword:mace"},
        {"keyword:molecular-dynamics", "keyword:mace"},
        {"keyword:dft", "keyword:training-data"},
    ]
    for pair in expected_pairs:
        if frozenset(pair) not in related_pairs:
            errors.append(f"Expected evidence-based concept link is missing: {sorted(pair)}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    args = parser.parse_args()
    graph = json.loads(args.graph.read_text(encoding="utf-8"))
    errors = validate(graph)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Validated {len(graph['nodes'])} nodes and {len(graph['edges'])} edges")
    print(json.dumps(graph["stats"], indent=2))


if __name__ == "__main__":
    main()
