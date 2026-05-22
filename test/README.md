# Unified Retrieval and Answerability Evaluation

This folder records the combined Phase B1/B2 test cases, scripts, reports, and historical outputs.

## Files

| Purpose | File |
| --- | --- |
| Phase A chunk quality script | `test/check_phase_a_chunks.py` |
| Phase A chunk quality report | `test/phase_a_chunk_quality_report.md` |
| Unified evaluation set | `test/eval_set.json` |
| Current unified report | `test/eval_report.md` |
| Historical unified reports | `test/eval_reports/` |
| Phase C LLM smoke cases | `test/llm_smoke_cases.json` |
| Current Phase C LLM smoke report | `test/llm_smoke_report.md` |
| Historical Phase C LLM smoke reports | `test/llm_smoke_reports/` |
| Phase C real LLM cases | `test/llm_real_cases.json` |
| Current Phase C real LLM report | `test/llm_real_report.md` |
| Historical Phase C real LLM reports | `test/llm_real_reports/` |
| Legacy retrieval-only evaluation set | `test/retrieval_eval_set.json` |
| Legacy answerability-only evaluation set | `test/answerability_eval_set.json` |

## Scripts

Run unified retrieval + answerability evaluation:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/scripts/evaluate.py
```

Each evaluation run writes `test/eval_report.md` and also saves a timestamped historical report under `test/eval_reports/`.

Run Phase C LLM-layer smoke evaluation:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/scripts/evaluate_llm.py
```

This uses the default `dry_run` provider, so it does not require an API key. It verifies answer-layer routing, prompt packaging, citations, temporal context, and short-memory follow-up behavior.

Run Phase C real LLM evaluation with Gemini:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
GEMINI_API_KEY=... python backend/scripts/evaluate_llm_real.py
```

This calls Gemini, retries transient failures once, and falls back from `gemini-2.5-flash` to `gemini-2.0-flash` if the primary model keeps failing.

## Retrieval Algorithm Summary

The current retrieval prototype is implemented in:

```text
backend/app/retriever.py
```

It does not call an LLM.

Current retrieval steps:

1. Normalize text:
   - lowercase.
   - treat hyphen, underscore, and slash as spaces.
   - expand selected aliases such as `convexhull -> convex hull`.
2. Run BM25 lexical retrieval.
3. Run sentence-transformers embedding retrieval.
4. Fuse normalized scores:
   - 45% BM25.
   - 55% embedding cosine similarity.
5. Boost phrase matches in title/path/content.
6. Boost `syllabus.md` and `calendar.md` for logistics questions.
7. Preserve temporal context for course-offering questions.

## Unified Evaluation Questions

Current baseline: **19 / 19 pass**.

The unified test cases combine the earlier retrieval-only and answerability-only questions into one set:

```text
test/eval_set.json
```

The current report groups cases by answerability decision:

```text
test/eval_report.md
```

## Answerability Gate Summary

The current answerability gate is implemented in:

```text
backend/app/answerability.py
```

It does not call an LLM. It decides whether retrieved chunks are strong enough to pass to a future answer generator.

Current statuses:

| Status | Meaning | Example |
| --- | --- | --- |
| `answerable` | Retrieved course evidence is strong enough. | What is convex hull? |
| `needs_time_context` | Query is course-offering specific and must state academic year/semester. | When is assignment 1 due? |
| `needs_clarification` | Query is too broad and should be narrowed. | Tell me about models |
| `weak_evidence` | Retrieved chunks are too weak for reliable answering. | Future no-result cases |
| `out_of_scope` | Query appears outside the course knowledge base. | What is the cafeteria menu today? |

Current thresholds and rule parameters:

| Parameter | Value | Used for |
| --- | ---: | --- |
| `strong_score` | `0.72` | Baseline threshold for strong retrieved evidence. |
| `weak_score` | `0.42` | Top score below this becomes `weak_evidence`. |
| `min_embedding_score` | `0.18` | If BM25 is near zero and embedding is below this, evidence is weak. |
| Multi-source closeness ratio | `0.72` | Results within 72% of the top score are considered close enough for multi-source detection. |
| Logistics temporal boost | `+0.25` | Applied to `syllabus.md` / `calendar.md` for logistics questions. |

Additional rules:

- Queries containing course logistics terms such as `assignment`, `quiz`, `exam`, `grading`, `deadline`, `schedule`, `calendar`, `syllabus`, `week`, `midterm`, or `review` require time context.
- The current time context for `syllabus.md` and `calendar.md` is **AY2025/2026 Semester 2**.
- Queries containing obvious outside-course terms such as `cafeteria`, `menu`, `weather`, `stock`, `restaurant`, `flight`, or `hotel` are marked `out_of_scope`.
- Broad short queries such as `Tell me about models` are marked `needs_clarification`.

## Current Grouped Report

The current report groups all 19 unified test cases by answerability class and lists each question with its score and top evidence.

Current groups:

- `answerable`
- `needs_time_context`
- `needs_clarification`
- `out_of_scope`

Use:

```text
test/eval_report.md
```

## Current Report Locations

Unified:

```text
test/eval_report.md
```

Phase C LLM smoke:

```text
test/llm_smoke_report.md
```

Phase C real LLM:

```text
test/llm_real_report.md
```
