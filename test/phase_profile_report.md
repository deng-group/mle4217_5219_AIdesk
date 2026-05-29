# Phase Runtime Profile

- Generated: **2026-05-29 12:52:42**
- Run directory: `test/profile_runs/20260529_125018`
- Scope: Phase B, Phase C, and Phase D on 5 fixed questions.
- Phase A is treated as completed and is not rerun by default.

## Summary

| Phase | Total | Main Components |
| --- | ---: | --- |
| Phase B | 17.679s | retriever_init=17.234s, 5_queries=0.445s |
| Phase C | 54.516s | provider=anthropic model=deepseek-v4-pro, prompt_build=0.001s, model_calls=54.515s |
| Phase D | 65.844s | api_init=0.003s, 5_api_posts=65.841s |
| Phase E | Not profiled | Deployment/pilot workflow has no local executable phase in this repo. |


## Phase B Details

- Chunks loaded: **401**
- Embedding backend: **sentence-transformers**
- Mean query time: **0.089s**
- Median query time: **0.082s**
- Slowest query time: **0.116s**

| Question | Retrieval | Answerability | Total | Status | Top Evidence |
| --- | ---: | ---: | ---: | --- | --- |
| What is convex hull? | 0.116s | 0.000s | 0.116s | `answerable` | `high_throughput/thermodynamics.md` `1.100` |
| How is Materials Project used in high-throughput screening? | 0.082s | 0.000s | 0.082s | `answerable` | `high_throughput/codes.md` `1.400` |
| What is the difference between molecular dynamics and Monte Carlo? | 0.097s | 0.000s | 0.097s | `answerable` | `models_and_theories_II/monte_carlo.md` `1.349` |
| When is assignment 1 due? | 0.073s | 0.000s | 0.073s | `needs_time_context` | `calendar.md` `1.250` |
| Tell me about models | 0.076s | 0.000s | 0.077s | `needs_clarification` | `models_and_theories_I/modelling.md` `0.748` |

## Phase C Details

- Provider/model: **anthropic / deepseek-v4-pro**
- Mean question time: **10.903s**
- Median question time: **12.711s**
- Slowest question time: **13.669s**

| Question | Prompt Build | Model Call | Total | OK | Status | Answer Chars |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| What is convex hull? | 0.000s | 13.669s | 13.669s | yes | `answerable` | 905 |
| How is Materials Project used in high-throughput screening? | 0.000s | 8.895s | 8.895s | yes | `answerable` | 479 |
| What is the difference between molecular dynamics and Monte Carlo? | 0.000s | 13.288s | 13.288s | yes | `answerable` | 1511 |
| When is assignment 1 due? | 0.000s | 5.952s | 5.952s | yes | `needs_time_context` | 294 |
| Tell me about models | 0.000s | 12.711s | 12.711s | yes | `needs_clarification` | 522 |

## Phase D Details

- Mean API POST time: **13.168s**
- Median API POST time: **11.370s**
- Slowest API POST time: **24.208s**
- Note: Uses Flask test client against `/api/answer` with the current `.env` provider/model, matching the book widget request path.

| Question | API POST | HTTP | OK | Provider | Model | Status |
| --- | ---: | ---: | --- | --- | --- | --- |
| What is convex hull? | 16.298s | 200 | yes | `anthropic` | `deepseek-v4-pro` | `answerable` |
| How is Materials Project used in high-throughput screening? | 24.208s | 200 | yes | `anthropic` | `deepseek-v4-pro` | `answerable` |
| What is the difference between molecular dynamics and Monte Carlo? | 11.370s | 200 | yes | `anthropic` | `deepseek-v4-pro` | `answerable` |
| When is assignment 1 due? | 6.271s | 200 | yes | `anthropic` | `deepseek-v4-pro` | `needs_time_context` |
| Tell me about models | 7.694s | 200 | yes | `anthropic` | `deepseek-v4-pro` | `needs_clarification` |

## Notes

Phase B includes retriever initialization, which may include loading the sentence-transformers model and reading/building the embedding index cache.
Phase C isolates prompt construction and configured model-provider latency using the Phase B outputs.
Phase D measures the local `/api/answer` route with the current `.env` provider/model, so it includes route overhead, retriever setup, and real model latency.