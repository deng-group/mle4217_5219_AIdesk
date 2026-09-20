# Nexus

Nexus is the standalone graph-based course explorer for MLE4217/5219. It lives
in this repository so it can reuse the existing RAG pipeline, but it does not
depend on or modify the sibling Jupyter Book repository.

The first implementation slice is the course knowledge graph in `graph/` and
the generated frontend-ready artifact in `data/course_graph.json`.

## Graph model

The graph has three node levels:

1. `chapter` — a course module such as Structures or High-Throughput Methods.
2. `topic` — a section within a chapter, such as Materials Project or MACE.
3. `keyword` — a global canonical concept shared by every chapter and topic.

Because keyword nodes are global, topics in different chapters connect through
the same concept instead of creating duplicate keyword nodes. The build also
adds topic-to-topic, chapter-to-chapter, and keyword-to-keyword `related` edges.
These relationships are deliberately undirected and do not assign a semantic
predicate. Every generated relationship carries evidence IDs that point back
to course chunks, plus a numerical strength that the interface can use for
progressive disclosure.

The graph is intentionally based on a reviewed concept taxonomy rather than the
raw automatically extracted `concepts` field. The raw field currently contains
code fragments and formatting artifacts that are unsuitable for student-facing
nodes.

## Rebuild and validate

From the repository root:

```bash
python3 nexus/graph/build_graph.py
python3 nexus/graph/validate_graph.py
```

The builder is deterministic: the same course chunks and taxonomy produce the
same node IDs, edges, and ordering.

## Visibility

Primary course chapters are marked `visibility: primary`. Review material is
kept as `secondary`, while repository metadata and figure-generation material
are `hidden`. A future frontend should start with primary chapter nodes and
expand topics and keywords on demand.
