# Phase A Complete: Knowledge Engineering

## Summary

Phase A has been rerun against the current `../MLE4217_5219_book` source tree.

The refreshed extraction includes all discoverable `.md` and `.ipynb` files in the book repository, including `syllabus.md` and `calendar.md`. The `AGENTS.md` file is intentionally excluded because it is agent guidance, not course content.

`syllabus.md` and `calendar.md` are marked as time-sensitive content. Their chunks include the course offering context from `syllabus.md`: **AY2025/2026 Semester 2**.

Standard generated/internal directories are ignored, including `.git`, `_build`, `.ipynb_checkpoints`, `__pycache__`, and `mle4217_5219_book.egg-info`.

## Deliverables Generated

### 1. `course_chunks.jsonl`

- 401 content chunks extracted from 110 source files.
- 284 Markdown chunks.
- 117 notebook chunks.
- Average chunk size: about 326 estimated tokens.
- Each chunk includes:
  - unique identifier.
  - text content.
  - source metadata.
  - module and section.
  - extracted concepts.
  - code blocks where applicable.
  - heading hierarchy.

### 2. `knowledge_graph.json`

- 322 nodes representing course structure:
- 324 nodes representing course structure:
  - 1 root node.
  - 16 module nodes.
  - 110 topic nodes.
  - 198 concept nodes.
- 1,694 edges connecting nodes:
  - hierarchy edges.
  - prerequisite edges.
  - contains edges.
  - related concept co-occurrence edges.

### 3. Validation Report

The latest validation report is:

```text
test/phase_a_chunk_quality_report.md
```

Current validation highlights:

- 401 / 401 chunks linked from the graph.
- 0 unlinked chunks.
- 0 missing required fields.
- 0 duplicate chunk IDs.
- 0 graph references to missing chunks.
- 0 current source files missing from chunks, after intentionally excluding only `AGENTS.md`.
- 0 chunk source files missing from the current repository.
- 362 unique extracted concepts.

## Module Coverage

The refreshed run includes these modules:

| Module | Chunks |
| --- | ---: |
| `computer` | 35 |
| `database` | 28 |
| `figures` | 26 |
| `final_review` | 7 |
| `high_throughput` | 25 |
| `machine_learning_I` | 31 |
| `machine_learning_II` | 23 |
| `machine_learning_potentials` | 27 |
| `midterm_review` | 7 |
| `models_and_theories_I` | 23 |
| `models_and_theories_II` | 26 |
| `optimization` | 30 |
| `orientation` | 29 |
| `programming` | 29 |
| `root` | 7 |
| `structures` | 48 |

## Key Features

### Content Extraction

- MyST Markdown parsing.
- Jupyter notebook support.
- Book-wide source discovery.
- Configurable exclusions.
- Chunking with paragraph and heading boundaries.
- Concept extraction from bold text, admonitions, and inline code.
- Heading hierarchy preservation.
- Code block extraction.

### Knowledge Graph

- Automatically generated module nodes from current chunks.
- Topic nodes derived from module and section metadata.
- Concept nodes derived from repeated extracted concepts.
- Typed relationships:
  - hierarchy.
  - prerequisite.
  - contains.
  - related.
- All chunks linked to graph nodes.

## Rebuild Commands

From the project root:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python scripts/phase_a/extract_content.py \
  --repo ../MLE4217_5219_book \
  --output data/phase_a/course_chunks.jsonl
```

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python scripts/phase_a/build_knowledge_graph.py \
  --chunks data/phase_a/course_chunks.jsonl \
  --output data/phase_a/knowledge_graph.json
```

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python test/check_phase_a_chunks.py
```

## Ready for Phase B

The refreshed data is ready for:

1. Embedding generation for all 401 chunks.
2. Vector database indexing.
3. BM25 or hybrid retrieval setup.
4. Node-aware retrieval using `knowledge_graph.json`.
5. Citation-aware RAG answer generation.
6. Answerability-gated QA evaluation.

For any future QA about schedule, grading, assignment timing, quizzes, exam logistics, or course arrangement, the system should explicitly confirm that the answer applies to **AY2025/2026 Semester 2** unless newer course-offering evidence is available.

**Phase A Status**: Complete and refreshed.
