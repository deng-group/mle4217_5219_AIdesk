# Answerability Evaluation Report

- Generated: **2026-05-21 13:41:11**
- Cases: **8**
- Passed: **8 / 8**
- Results shown per case: **3**

## PASS: `convex_hull_answerable`

Query: `What is convex hull?`

Decision: **answerable**

Reason: Retrieved course evidence is strong enough.

Confidence: `1.100`

Multi-source: `False`

Top results:
- 1. `high_throughput/thermodynamics.md_1` | `high_throughput/thermodynamics.md` | score=1.100
- 2. `high_throughput/introduction.md_1` | `high_throughput/introduction.md` | score=0.624
- 3. `final_review/index.md_1` | `final_review/index.md` | score=0.600

## PASS: `assignment_due_time_context`

Query: `When is assignment 1 due?`

Decision: **needs_time_context** | AY2025/2026 Semester 2

Reason: Course-offering answer should state the retrieved academic year/semester.

Confidence: `1.250`

Multi-source: `False`

Top results:
- 1. `calendar.md_1` | `calendar.md` | score=1.250 | AY2025/2026 Semester 2
- 2. `syllabus.md_0` | `syllabus.md` | score=0.992 | AY2025/2026 Semester 2
- 3. `midterm_review/index.md_0` | `midterm_review/index.md` | score=0.477

## PASS: `grading_time_context`

Query: `What is the grading breakdown?`

Decision: **needs_time_context** | AY2025/2026 Semester 2

Reason: Course-offering answer should state the retrieved academic year/semester.

Confidence: `1.100`

Multi-source: `False`

Top results:
- 1. `syllabus.md_0` | `syllabus.md` | score=1.100 | AY2025/2026 Semester 2
- 2. `calendar.md_1` | `calendar.md` | score=1.038 | AY2025/2026 Semester 2
- 3. `machine_learning_potentials/index.md_0` | `machine_learning_potentials/index.md` | score=0.513

## PASS: `materials_project_mace_multi_source`

Query: `How is Materials Project data related to MACE?`

Decision: **answerable**

Reason: Retrieved course evidence is strong enough.

Confidence: `1.558`

Multi-source: `True`

Top results:
- 1. `database/materials_project.ipynb_2` | `database/materials_project.ipynb` | score=1.558
- 2. `machine_learning_potentials/umlp.md_1` | `machine_learning_potentials/umlp.md` | score=1.225
- 3. `database/materials_project.ipynb_0` | `database/materials_project.ipynb` | score=1.555

## PASS: `md_mc_answerable`

Query: `What is the difference between molecular dynamics and Monte Carlo?`

Decision: **answerable**

Reason: Retrieved course evidence is strong enough.

Confidence: `1.349`

Multi-source: `True`

Top results:
- 1. `models_and_theories_II/monte_carlo.md_3` | `models_and_theories_II/monte_carlo.md` | score=1.349
- 2. `models_and_theories_II/kmc.md_2` | `models_and_theories_II/kmc.md` | score=1.275
- 3. `models_and_theories_II/statistical_mech.md_4` | `models_and_theories_II/statistical_mech.md` | score=1.212

## PASS: `cafeteria_out_of_scope`

Query: `What is the cafeteria menu today?`

Decision: **out_of_scope**

Reason: The query appears outside the course knowledge base.

Confidence: `0.721`

Multi-source: `True`

Top results:
- 1. `computer/hpc.md_6` | `computer/hpc.md` | score=0.721
- 2. `computer/history.md_1` | `computer/history.md` | score=0.716
- 3. `structures/vesta.md_1` | `structures/vesta.md` | score=0.691

## PASS: `weather_out_of_scope`

Query: `What is the weather today?`

Decision: **out_of_scope**

Reason: The query appears outside the course knowledge base.

Confidence: `0.806`

Multi-source: `True`

Top results:
- 1. `computer/hpc.md_6` | `computer/hpc.md` | score=0.806
- 2. `orientation/introduction.md_0` | `orientation/introduction.md` | score=0.706
- 3. `computer/hardware.md_4` | `computer/hardware.md` | score=0.625

## PASS: `broad_models_clarification`

Query: `Tell me about models`

Decision: **needs_clarification**

Reason: The query is broad and should be narrowed to a concept, module, or task.

Confidence: `0.748`

Multi-source: `True`

Top results:
- 1. `models_and_theories_I/modelling.md_0` | `models_and_theories_I/modelling.md` | score=0.748
- 2. `orientation/orientation.md_3` | `orientation/orientation.md` | score=0.669
- 3. `final_review/models_and_theories.md_0` | `final_review/models_and_theories.md` | score=0.513
