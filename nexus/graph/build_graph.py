#!/usr/bin/env python3
"""Build the student-facing Nexus knowledge graph from course RAG chunks."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHUNKS = REPO_ROOT / "data/phase_a/course_chunks.jsonl"
DEFAULT_TAXONOMY = Path(__file__).with_name("concept_taxonomy.json")
DEFAULT_OUTPUT = REPO_ROOT / "nexus/data/course_graph.json"

# These concepts remain visible and connected to their course topics, but are
# too broad to justify an automatic topic-to-topic bridge by themselves.
BRIDGE_STOP_CONCEPTS = {
    "ase",
    "database",
    "feature",
    "git",
    "github",
    "interface",
    "jupyter-notebook",
    "machine-learning",
    "matplotlib",
    "molecule",
    "numpy",
    "optimization",
    "pandas",
    "pymatgen",
    "python",
    "version-control",
    "workflow",
}

CHAPTER_ORDER = [
    "orientation",
    "programming",
    "computer",
    "database",
    "structures",
    "models_and_theories_I",
    "models_and_theories_II",
    "optimization",
    "high_throughput",
    "machine_learning_I",
    "machine_learning_II",
    "machine_learning_potentials",
    "midterm_review",
    "final_review",
    "root",
    "figures",
]

CHAPTER_METADATA = {
    "orientation": ("Orientation", "Course introduction, setup, and learning environment."),
    "programming": ("Programming", "Python and scientific programming foundations."),
    "computer": ("Computer and Computation", "Hardware, software, version control, and performance."),
    "database": ("Database", "Materials databases, data formats, querying, and analysis."),
    "structures": ("Structures", "Crystal structures, symmetry, defects, interfaces, and representations."),
    "models_and_theories_I": ("Models and Theories I", "Atomistic models, force fields, and electronic structure."),
    "models_and_theories_II": ("Models and Theories II", "Statistical mechanics, molecular dynamics, and Monte Carlo."),
    "optimization": ("Optimization", "Energy landscapes and local and global optimization methods."),
    "high_throughput": ("High-Throughput Methods", "Automated workflows, thermodynamics, and materials discovery."),
    "machine_learning_I": ("Machine Learning I", "Machine-learning tasks, features, models, and validation."),
    "machine_learning_II": ("Machine Learning II", "Graphs, graph neural networks, and generative models."),
    "machine_learning_potentials": ("Machine Learning Potentials", "Interatomic machine-learning models and their training."),
    "midterm_review": ("Midterm Review", "Review material for the first part of the course."),
    "final_review": ("Final Review", "Review material connecting the full course."),
    "root": ("Course Information", "Syllabus, calendar, and course-level information."),
    "figures": ("Figure Sources", "Supporting figure-generation material."),
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def visibility_for(module: str) -> str:
    if module in {"root", "figures"}:
        return "hidden"
    if module in {"midterm_review", "final_review"}:
        return "secondary"
    return "primary"


def topic_id(module: str, section: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", f"{module}-{section}".lower()).strip("-")
    return f"topic:{cleaned}"


def chapter_id(module: str) -> str:
    return f"chapter:{module.lower()}"


def keyword_id(concept: str) -> str:
    return f"keyword:{concept}"


def normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("_", " ")).strip()


def alias_pattern(alias: str) -> re.Pattern[str]:
    normalized = normalized_text(alias)
    escaped = re.escape(normalized).replace(r"\ ", r"[\s\-/]+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


def detect_concepts(text: str, taxonomy: list[dict]) -> dict[str, int]:
    searchable = normalized_text(text)
    found = {}
    for concept in taxonomy:
        count = 0
        for pattern in concept["patterns"]:
            count += len(pattern.findall(searchable))
        if count:
            found[concept["id"]] = count
    return found


def edge_key(source: str, target: str, edge_type: str) -> tuple[str, str, str]:
    if edge_type == "related" and source > target:
        source, target = target, source
    return source, target, edge_type


def top_symmetric_pairs(
    candidates: list[tuple[float, str, str, dict]],
    max_per_node: int,
) -> list[tuple[float, str, str, dict]]:
    chosen = []
    degree = Counter()
    for score, source, target, metadata in sorted(candidates, reverse=True):
        if degree[source] >= max_per_node or degree[target] >= max_per_node:
            continue
        chosen.append((score, source, target, metadata))
        degree[source] += 1
        degree[target] += 1
    return chosen


def build_graph(chunks: list[dict], raw_taxonomy: dict) -> dict:
    taxonomy = []
    for item in raw_taxonomy["concepts"]:
        entry = dict(item)
        entry["patterns"] = [alias_pattern(alias) for alias in item["aliases"]]
        taxonomy.append(entry)
    taxonomy_by_id = {item["id"]: item for item in taxonomy}

    chunks_by_module: dict[str, list[dict]] = defaultdict(list)
    chunks_by_topic: dict[tuple[str, str], list[dict]] = defaultdict(list)
    chunk_concepts: dict[str, dict[str, int]] = {}
    concept_chunks: dict[str, list[str]] = defaultdict(list)
    concept_mentions = Counter()

    for chunk in chunks:
        module = chunk.get("module", "root")
        section = chunk.get("section", "unknown")
        chunks_by_module[module].append(chunk)
        chunks_by_topic[(module, section)].append(chunk)
        search_text = "\n".join(
            [str(chunk.get("title", "")), str(chunk.get("section", "")), str(chunk.get("content", ""))]
        )
        matches = detect_concepts(search_text, taxonomy)
        chunk_concepts[chunk["chunk_id"]] = matches
        for concept, count in matches.items():
            concept_chunks[concept].append(chunk["chunk_id"])
            concept_mentions[concept] += count

    active_concepts = {concept for concept, ids in concept_chunks.items() if ids}
    nodes = []
    edges = []
    edge_keys = set()

    ordered_modules = [module for module in CHAPTER_ORDER if module in chunks_by_module]
    ordered_modules.extend(sorted(module for module in chunks_by_module if module not in ordered_modules))

    topic_concepts: dict[str, set[str]] = {}
    topic_evidence: dict[str, dict[str, list[str]]] = {}
    module_topics: dict[str, list[str]] = defaultdict(list)
    module_concepts: dict[str, set[str]] = defaultdict(set)

    for module_index, module in enumerate(ordered_modules):
        module_chunks = chunks_by_module[module]
        label, description = CHAPTER_METADATA.get(
            module,
            (module.replace("_", " ").title(), f"Course material for {module.replace('_', ' ')}."),
        )
        section_keys = sorted(
            {(chunk.get("section", "unknown"), chunk.get("title") or chunk.get("section", "unknown")) for chunk in module_chunks},
            key=lambda item: (item[0] == "index", item[0]),
        )
        chapter_keyword_counts = Counter()
        for chunk in module_chunks:
            chapter_keyword_counts.update(chunk_concepts[chunk["chunk_id"]])
        chapter_keywords = sorted(chapter_keyword_counts)
        module_concepts[module].update(chapter_keywords)

        nodes.append(
            {
                "id": chapter_id(module),
                "type": "chapter",
                "label": label,
                "description": description,
                "module": module,
                "order": module_index,
                "visibility": visibility_for(module),
                "chunk_ids": [chunk["chunk_id"] for chunk in module_chunks],
                "source_files": sorted({chunk["file_path"] for chunk in module_chunks}),
                "keyword_ids": [keyword_id(value) for value in chapter_keywords],
            }
        )

        for section, title in section_keys:
            section_chunks = chunks_by_topic[(module, section)]
            node_id = topic_id(module, section)
            module_topics[module].append(node_id)
            evidence: dict[str, list[str]] = defaultdict(list)
            keyword_counts = Counter()
            for chunk in section_chunks:
                keyword_counts.update(chunk_concepts[chunk["chunk_id"]])
                for concept in chunk_concepts[chunk["chunk_id"]]:
                    evidence[concept].append(chunk["chunk_id"])
            concepts = set(keyword_counts)
            topic_concepts[node_id] = concepts
            topic_evidence[node_id] = evidence
            topic_visibility = visibility_for(module)
            if section == "index" and topic_visibility == "primary":
                topic_visibility = "secondary"
            nodes.append(
                {
                    "id": node_id,
                    "type": "topic",
                    "label": str(title).strip(),
                    "description": f"{str(title).strip()} in {label}.",
                    "module": module,
                    "section": section,
                    "chapter_id": chapter_id(module),
                    "visibility": topic_visibility,
                    "chunk_ids": [chunk["chunk_id"] for chunk in section_chunks],
                    "source_files": sorted({chunk["file_path"] for chunk in section_chunks}),
                    "keyword_ids": [keyword_id(value) for value in sorted(concepts)],
                }
            )
            edges.append(
                {
                    "id": f"contains:{chapter_id(module)}:{node_id}",
                    "source": chapter_id(module),
                    "target": node_id,
                    "type": "contains",
                    "label": "contains topic",
                    "weight": 1.0,
                    "evidence": {"chunk_ids": [chunk["chunk_id"] for chunk in section_chunks]},
                }
            )

            for concept, count in sorted(keyword_counts.items()):
                target = keyword_id(concept)
                edges.append(
                    {
                        "id": f"mentions:{node_id}:{target}",
                        "source": node_id,
                        "target": target,
                        "type": "mentions",
                        "label": "covers concept",
                        "weight": round(min(1.0, 0.45 + math.log1p(count) / 4), 4),
                        "evidence": {"chunk_ids": sorted(set(evidence[concept]))},
                        "mention_count": count,
                    }
                )

        for concept, count in sorted(chapter_keyword_counts.items()):
            target = keyword_id(concept)
            supporting_topics = [
                node_id for node_id in module_topics[module] if concept in topic_concepts[node_id]
            ]
            edges.append(
                {
                    "id": f"covers:{chapter_id(module)}:{target}",
                    "source": chapter_id(module),
                    "target": target,
                    "type": "covers",
                    "label": "covers concept",
                    "weight": round(min(1.0, 0.4 + 0.12 * len(supporting_topics) + math.log1p(count) / 10), 4),
                    "evidence": {
                        "chunk_ids": sorted(
                            chunk["chunk_id"]
                            for chunk in module_chunks
                            if concept in chunk_concepts[chunk["chunk_id"]]
                        ),
                        "topic_ids": supporting_topics,
                    },
                    "mention_count": count,
                }
            )

    for concept in sorted(active_concepts):
        item = taxonomy_by_id[concept]
        linked_topics = sorted(node_id for node_id, concepts in topic_concepts.items() if concept in concepts)
        linked_chapters = sorted(
            chapter_id(module) for module, concepts in module_concepts.items() if concept in concepts
        )
        nodes.append(
            {
                "id": keyword_id(concept),
                "type": "keyword",
                "label": item["label"],
                "description": f"A course concept in the {item['category'].replace('-', ' ')} group.",
                "category": item["category"],
                "aliases": item["aliases"],
                "visibility": "primary",
                "chunk_ids": sorted(set(concept_chunks[concept])),
                "topic_ids": linked_topics,
                "chapter_ids": linked_chapters,
                "mention_count": concept_mentions[concept],
            }
        )

    # Course sequence is descriptive, not a claim that every chapter is a prerequisite.
    primary_modules = [module for module in ordered_modules if visibility_for(module) == "primary"]
    for left, right in zip(primary_modules, primary_modules[1:]):
        edges.append(
            {
                "id": f"sequence:{chapter_id(left)}:{chapter_id(right)}",
                "source": chapter_id(left),
                "target": chapter_id(right),
                "type": "sequence",
                "label": "followed by",
                "weight": 0.5,
                "evidence": {"source": "course chapter order"},
            }
        )

    # Keyword relationships are intentionally undirected and semantically
    # neutral. The graph records only that two concepts share course evidence;
    # it does not guess the nature or direction of the relationship.
    keyword_candidates = []
    active_list = sorted(active_concepts)
    concept_topic_sets = {
        concept: {node_id for node_id, concepts in topic_concepts.items() if concept in concepts}
        for concept in active_list
    }
    concept_chunk_sets = {concept: set(concept_chunks[concept]) for concept in active_list}
    for index, left in enumerate(active_list):
        for right in active_list[index + 1 :]:
            shared_topics = concept_topic_sets[left] & concept_topic_sets[right]
            shared_chunks = concept_chunk_sets[left] & concept_chunk_sets[right]
            if not shared_topics or not shared_chunks:
                continue
            denominator = math.sqrt(len(concept_topic_sets[left]) * len(concept_topic_sets[right]))
            score = len(shared_topics) / denominator if denominator else 0.0
            if score < 0.10:
                continue
            keyword_candidates.append(
                (
                    score,
                    keyword_id(left),
                    keyword_id(right),
                    {
                        "chunk_ids": sorted(shared_chunks)[:8],
                        "topic_ids": sorted(shared_topics),
                    },
                )
            )
    for score, source, target, evidence in sorted(keyword_candidates, reverse=True):
        edges.append(
            {
                "id": f"related:{source}:{target}",
                "source": source,
                "target": target,
                "type": "related",
                "label": "related",
                "basis": "shared_course_evidence",
                "weight": round(score, 4),
                "evidence": evidence,
            }
        )

    # Cross-chapter topic bridges are based on at least two shared curated concepts.
    topic_candidates = []
    topic_ids = sorted(topic_concepts)
    topic_modules = {node_id: node_id.split(":", 1)[1].split("-", 1)[0] for node_id in topic_ids}
    # Use the actual module mapping because module IDs can contain underscores.
    for module, ids in module_topics.items():
        for node_id in ids:
            topic_modules[node_id] = module
    for index, left in enumerate(topic_ids):
        if visibility_for(topic_modules[left]) != "primary":
            continue
        for right in topic_ids[index + 1 :]:
            if topic_modules[left] == topic_modules[right] or visibility_for(topic_modules[right]) != "primary":
                continue
            shared = (topic_concepts[left] & topic_concepts[right]) - BRIDGE_STOP_CONCEPTS
            if len(shared) < 2:
                continue
            union = topic_concepts[left] | topic_concepts[right]
            score = len(shared) / max(len(union), 1)
            if score < 0.12:
                continue
            topic_candidates.append(
                (
                    score,
                    left,
                    right,
                    {"shared_keyword_ids": [keyword_id(value) for value in sorted(shared)]},
                )
            )
    for score, source, target, evidence in top_symmetric_pairs(topic_candidates, max_per_node=3):
        edges.append(
            {
                "id": f"related:{source}:{target}",
                "source": source,
                "target": target,
                "type": "related",
                "label": "related",
                "basis": "shared_keywords",
                "weight": round(score, 4),
                "evidence": evidence,
            }
        )

    # Chapter bridges summarize the concepts that span two course chapters.
    chapter_candidates = []
    primary_chapters = [module for module in ordered_modules if visibility_for(module) == "primary"]
    for index, left in enumerate(primary_chapters):
        for right in primary_chapters[index + 1 :]:
            shared = (module_concepts[left] & module_concepts[right]) - BRIDGE_STOP_CONCEPTS
            if len(shared) < 3:
                continue
            union = module_concepts[left] | module_concepts[right]
            score = len(shared) / max(len(union), 1)
            chapter_candidates.append(
                (
                    score,
                    chapter_id(left),
                    chapter_id(right),
                    {"shared_keyword_ids": [keyword_id(value) for value in sorted(shared)]},
                )
            )
    for score, source, target, evidence in top_symmetric_pairs(chapter_candidates, max_per_node=3):
        edges.append(
            {
                "id": f"related:{source}:{target}",
                "source": source,
                "target": target,
                "type": "related",
                "label": "related",
                "basis": "shared_keywords",
                "weight": round(score, 4),
                "evidence": evidence,
            }
        )

    # Remove accidental duplicate edges while keeping deterministic ordering.
    unique_edges = []
    for edge in edges:
        key = edge_key(edge["source"], edge["target"], edge["type"])
        if key in edge_keys:
            continue
        edge_keys.add(key)
        unique_edges.append(edge)

    nodes.sort(key=lambda node: (node["type"], node["id"]))
    unique_edges.sort(key=lambda edge: (edge["type"], edge["source"], edge["target"]))
    node_counts = Counter(node["type"] for node in nodes)
    edge_counts = Counter(edge["type"] for edge in unique_edges)
    cross_chapter_topics = sum(
        1
        for edge in unique_edges
        if edge["type"] == "related" and edge["source"].startswith("topic:")
    )

    return {
        "schema_version": "1.0",
        "course": {"code": "MLE4217/5219", "title": "Materials Informatics"},
        "source": {
            "chunks": str(DEFAULT_CHUNKS.relative_to(REPO_ROOT)),
            "taxonomy": str(DEFAULT_TAXONOMY.relative_to(REPO_ROOT)),
            "taxonomy_version": raw_taxonomy["version"],
        },
        "display_defaults": {
            "initial_node_types": ["chapter"],
            "initial_visibility": ["primary"],
            "expand_on_select": ["topic", "keyword"],
            "hidden_edge_types": ["covers", "mentions", "related"],
        },
        "stats": {
            "nodes": len(nodes),
            "edges": len(unique_edges),
            "node_types": dict(sorted(node_counts.items())),
            "edge_types": dict(sorted(edge_counts.items())),
            "cross_chapter_topic_bridges": cross_chapter_topics,
        },
        "nodes": nodes,
        "edges": unique_edges,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    chunks = load_jsonl(args.chunks)
    taxonomy = json.loads(args.taxonomy.read_text(encoding="utf-8"))
    graph = build_graph(chunks, taxonomy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(graph["stats"], indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
