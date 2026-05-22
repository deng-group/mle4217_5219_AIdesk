# Phase B1 Retrieval Prototype

This backend prototype does retrieval only. It does not call an LLM.

The current algorithm is:

1. Load Phase A chunks from `data/phase_a/course_chunks.jsonl`.
2. Normalize query and chunk text:
   - lowercase.
   - treat hyphen/underscore/slash as spaces.
   - expand a few known aliases such as `convexhull -> convex hull`.
3. Run BM25 lexical retrieval.
4. Run sentence-transformers embedding retrieval.
5. Normalize and fuse scores:
   - 45% BM25.
   - 55% embedding cosine similarity.
6. Boost time-sensitive syllabus/calendar chunks for logistics questions.
7. Return ranked chunks with:
   - chunk id.
   - file path.
   - score.
   - temporal context if present.
   - content preview.

Run:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/app/retriever.py
```

Run custom queries:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/app/retriever.py "What is convex hull?" "When is assignment 1 due?"
```

## Query Pipeline

The stable retrieval + answerability pipeline lives at:

```text
backend/app/query_pipeline.py
```

It returns JSON with:

- `status`
- `next_action`
- `reason`
- `confidence`
- `temporal_context`
- `multi_source`
- `evidence`

Run one query:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/scripts/query.py "how to construct a BaTiO3 structure?"
```

## Phase C Prompt Builder

The prompt builder lives at:

```text
backend/app/prompt_builder.py
```

It does not call an LLM. It builds a structured prompt package from the query pipeline result, including:

- system instruction.
- answerability status.
- required LLM action.
- answer policy.
- evidence chunks.
- temporal context when needed.
- optional short memory from the current open session.

Evidence policy:

- Retrieval/test reports use chunk IDs and scores for inspection.
- Prompt construction uses full chunk content, not truncated previews.
- By default, all retrieved chunks with score `>= 0.60` are included as LLM evidence.
- There is currently no token cap; this keeps code blocks complete during early testing.
- Student-facing answers should cite source titles and file paths, not raw internal chunk IDs.
- Student-facing answers should start by pointing to the relevant course source location.
- If multiple sources are relevant, the answer should list only the top 3 sources first.

Run one prompt package:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/scripts/build_prompt.py "how to construct a BaTiO3 structure?"
```

Adjust the evidence threshold:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/scripts/build_prompt.py "how to construct a BaTiO3 structure?" \
--evidence-threshold 0.60
```

## Phase C Answer Generator

The answer-generation layer lives at:

```text
backend/app/answer_generator.py
```

It connects:

- `QueryPipeline`
- `PromptBuilder`
- a pluggable LLM provider

Current providers:

| Provider | Purpose |
| --- | --- |
| `dry_run` | Default local provider. Does not call an LLM; returns a deterministic answer preview for testing routing, evidence, citations, temporal context, and memory packaging. |
| `openai` | Optional OpenAI Responses API provider. Requires the `openai` Python package, `OPENAI_API_KEY`, and an explicit model through `--model` or `OPENAI_MODEL`. |
| `gemini` | Optional Google Gemini REST provider. Requires `GEMINI_API_KEY` or `GOOGLE_API_KEY`; defaults to `gemini-2.5-flash`. |
| `anthropic` | Optional Anthropic-compatible Messages API provider. Requires `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY`; defaults to `claude-sonnet-4-6` for the current matsci relay. |

Run one dry-run answer package:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/scripts/answer.py "how to construct a BaTiO3 structure?"
```

Run with prompt details included:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/scripts/answer.py "When is assignment 1 due?" --include-prompt
```

Run with Gemini:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
GEMINI_API_KEY=... python backend/scripts/answer.py \
"how to construct a BaTiO3 structure?" --provider gemini --model gemini-2.5-flash
```

Run with an Anthropic-compatible endpoint:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
ANTHROPIC_BASE_URL=... ANTHROPIC_AUTH_TOKEN=... \
python backend/scripts/answer.py "What is convex hull?" \
--provider anthropic --model <supported-model>
```

Memory policy:

- Short memory is limited to the current open session/window.
- Memory is not shared across students.
- Memory is not persistent across closed/reopened windows.
- Future UI should tell students that closing or reopening the window clears the conversation memory.

## Unified Evaluation

The unified evaluation notes are in:

```text
test/README.md
```

The unified retrieval + answerability evaluation set lives at:

```text
test/eval_set.json
```

Run it with:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/scripts/evaluate.py
```

The current report is written to:

```text
test/eval_report.md
```

Each run also saves a timestamped historical report under:

```text
test/eval_reports/
```

Current baseline:

- 19 total cases.
- 19 / 19 pass.
- The report is grouped by answerability status and lists each question with score and top evidence.

## Phase C LLM Smoke Evaluation

The Phase C LLM-layer smoke cases live at:

```text
test/llm_smoke_cases.json
```

Run them with the default dry-run provider:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/scripts/evaluate_llm.py
```

The report is written to:

```text
test/llm_smoke_report.md
```

Each run also saves a timestamped historical report under:

```text
test/llm_smoke_reports/
```

This is where Phase C tests for short-memory follow-up questions belong. The unified retrieval evaluation should stay focused on retrieval and answerability.

## Phase C Real LLM Evaluation

The real LLM evaluation cases live at:

```text
test/llm_real_cases.json
```

Run them with Gemini:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
GEMINI_API_KEY=... python backend/scripts/evaluate_llm_real.py
```

The script uses:

- primary model: `gemini-2.5-flash`
- fallback model: `gemini-2.0-flash`
- retry before fallback: 1 retry by default
- retry delay: 5 seconds by default

The report is written to:

```text
test/llm_real_report.md
```

Each run also saves a timestamped historical report under:

```text
test/llm_real_reports/
```

This report is for manual answer-quality review. It records each answer, top sources, model used, and retry/fallback attempts.

## Answerability Gate

The first answerability gate lives at:

```text
backend/app/answerability.py
```

It does not call an LLM. It classifies retrieved evidence into statuses such as:

- `answerable`
- `needs_time_context`
- `needs_clarification`
- `weak_evidence`
- `out_of_scope`

Run sample decisions directly:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
python backend/app/answerability.py
```

## Deferred TODOs

These are intentionally parked until the first project prototype is working end to end.

### Typo, spacing, and term normalization

- Improve tolerance for misspellings such as `convax hull`, `Matrials Project`, or `Mote Carlo`.
- Expand the alias table for common spacing and punctuation variants:
  - `convexhull` -> `convex hull`
  - `highthroughput` -> `high throughput`
  - `materialsproject` -> `materials project`
  - `machinelearning` -> `machine learning`
- Consider a course-concept dictionary built from Phase A concepts and titles.
- Add conservative fuzzy matching only when confidence is high, so the retriever does not accidentally rewrite material names, formulas, code identifiers, or acronyms.
- Add tests for case handling, hyphen/underscore handling, joined words, and common student typos.

### Multi-chunk and multi-file questions

- Decide how to return evidence when a question requires several chunks from different files.
- Keep multiple chunks when they support different parts of the question, instead of forcing all evidence into one source.
- Add grouping by concept, module, or graph node so the future LLM can synthesize across related evidence cleanly.
- Track when retrieved chunks disagree or answer different interpretations of the question.

### No-result and weak-result behavior

- Define score thresholds for "probably answerable" vs. "weak evidence".
- Return a structured insufficient-evidence result when no relevant chunks are found.
- Suggest nearby concepts or ask a clarification question rather than returning unrelated chunks.
- Later, allow web fallback only when the question is external, current, or not covered by the course database.

### API provider reliability

- If the final system uses an external API provider such as Gemini or OpenAI, add retry handling for transient provider failures.
- In particular, handle Gemini `503 UNAVAILABLE` / high-demand responses with a short retry policy.
- Add model fallback so `gemini-2.5-flash` can fall back to a configured backup model such as `gemini-2.0-flash` when the primary model is temporarily unavailable.
- Keep these failures visible in logs and test reports so API instability is not mistaken for retrieval or prompt failure.

### Student-facing source display

- The current prompt tells the model to list at most the top 3 sources at the beginning of each answer.
- Revisit whether 3 is the right number after testing with students and instructors.
- When this becomes a web window/plugin, make source titles clickable so students can jump directly to the relevant course chapter or section.
- The Jupyter Book widget lives in the sibling book repo at `../MLE4217_5219_book/ai_agent_widget/` and is injected after HTML build. When updating the book, preserve this folder and the Makefile post-build injection step.
- After rebuilding the book, verify that the widget still appears on generated HTML pages and can reach the backend API URL.

### Answer length policy

- Decide when answers should be short, medium, or detailed.
- Concept-definition questions may need concise answers.
- Code or workflow questions may need longer step-by-step answers with complete code.
- Review/exam-prep questions may need structured summaries.
- Clarification, weak-evidence, and out-of-scope responses should usually be short.
- Add tests for answer length after the first web prototype is usable.

### Follow-up question recommendations

- After answering a student question, recommend a small set of related follow-up questions.
- Use retrieved chunks, graph neighbors, prerequisite nodes, and related concepts to generate follow-up candidates.
- Keep follow-ups pedagogically useful, for example:
  - definition -> application question.
  - application -> implementation/code question.
  - single concept -> bridge question to a connected concept.
  - logistics question -> relevant next deadline or course policy question.
- Store enough metadata so the system knows how each recommended follow-up should be retrieved and answered.
- Add evaluation examples for follow-up question quality after the first answer-generation prototype exists.
