# Retrieval Evaluation Report

- Cases: **16**
- Passed: **16 / 16**
- Expected failures: **1**
- Top-k evaluated: **5**
- Weak-result threshold: **0.25**

## PASS: `convex_hull_definition`

Query: `What is convex hull?`

Notes: Definition-style conceptual question.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `high_throughput/thermodynamics.md_1` | `high_throughput/thermodynamics.md` | score=1.100
- 2. `high_throughput/thermodynamics.md_2` | `high_throughput/thermodynamics.md` | score=0.806
- 3. `high_throughput/introduction.md_1` | `high_throughput/introduction.md` | score=0.624
- 4. `final_review/index.md_1` | `final_review/index.md` | score=0.600
- 5. `optimization/introduction.md_2` | `optimization/introduction.md` | score=0.549

## PASS: `convex_hull_joined_word`

Query: `convexhull`

Notes: Checks joined-word alias handling.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `high_throughput/thermodynamics.md_1` | `high_throughput/thermodynamics.md` | score=1.100
- 2. `high_throughput/thermodynamics.md_2` | `high_throughput/thermodynamics.md` | score=0.812
- 3. `final_review/index.md_1` | `final_review/index.md` | score=0.690
- 4. `high_throughput/introduction.md_1` | `high_throughput/introduction.md` | score=0.669
- 5. `optimization/introduction.md_2` | `optimization/introduction.md` | score=0.637

## PASS: `materials_project_usage`

Query: `How is Materials Project used?`

Notes: Should prefer Materials Project over Materials Genome Initiative.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `database/materials_project.ipynb_0` | `database/materials_project.ipynb` | score=1.095
- 2. `orientation/introduction.md_4` | `orientation/introduction.md` | score=1.000
- 3. `database/materials_project.ipynb_2` | `database/materials_project.ipynb` | score=0.932
- 4. `machine_learning_potentials/umlp.md_1` | `machine_learning_potentials/umlp.md` | score=0.932
- 5. `database/materials_database.md_1` | `database/materials_database.md` | score=0.820

## PASS: `md_mc_comparison`

Query: `What is the difference between molecular dynamics and Monte Carlo?`

Notes: Comparison query should find the MC vs MD comparison table.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `models_and_theories_II/monte_carlo.md_3` | `models_and_theories_II/monte_carlo.md` | score=1.349
- 2. `models_and_theories_II/monte_carlo.md_0` | `models_and_theories_II/monte_carlo.md` | score=1.316
- 3. `models_and_theories_II/kmc.md_2` | `models_and_theories_II/kmc.md` | score=1.275
- 4. `models_and_theories_II/statistical_mech.md_4` | `models_and_theories_II/statistical_mech.md` | score=1.212
- 5. `models_and_theories_II/kmc.md_0` | `models_and_theories_II/kmc.md` | score=1.098

## PASS: `assignment_due`

Query: `When is assignment 1 due?`

Notes: Logistics query must retrieve time-sensitive course-offering evidence.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `calendar.md_1` | `calendar.md` | score=1.250 | AY2025/2026 Semester 2
- 2. `syllabus.md_0` | `syllabus.md` | score=0.992 | AY2025/2026 Semester 2
- 3. `calendar.md_0` | `calendar.md` | score=0.886 | AY2025/2026 Semester 2
- 4. `midterm_review/index.md_0` | `midterm_review/index.md` | score=0.477
- 5. `syllabus.md_1` | `syllabus.md` | score=0.471 | AY2025/2026 Semester 2

## PASS: `grading_breakdown`

Query: `What is the grading breakdown?`

Notes: Syllabus query must preserve academic-year context.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `syllabus.md_0` | `syllabus.md` | score=1.100 | AY2025/2026 Semester 2
- 2. `calendar.md_1` | `calendar.md` | score=1.038 | AY2025/2026 Semester 2
- 3. `calendar.md_0` | `calendar.md` | score=0.917 | AY2025/2026 Semester 2
- 4. `syllabus.md_1` | `syllabus.md` | score=0.644 | AY2025/2026 Semester 2
- 5. `machine_learning_potentials/index.md_0` | `machine_learning_potentials/index.md` | score=0.513

## PASS: `midterm_topics`

Query: `What topics are covered before the midterm review?`

Notes: Can be answered from calendar and review material.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `midterm_review/index.md_1` | `midterm_review/index.md` | score=0.996
- 2. `midterm_review/orientation.md_0` | `midterm_review/orientation.md` | score=0.959
- 3. `midterm_review/index.md_0` | `midterm_review/index.md` | score=0.931
- 4. `midterm_review/computer.md_0` | `midterm_review/computer.md` | score=0.904
- 5. `calendar.md_0` | `calendar.md` | score=0.854 | AY2025/2026 Semester 2

## PASS: `descriptors_ml`

Query: `Why are descriptors important in machine learning for materials?`

Notes: ML feature/descriptors question.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `machine_learning_I/features.md_0` | `machine_learning_I/features.md` | score=1.316
- 2. `machine_learning_I/index.md_0` | `machine_learning_I/index.md` | score=1.203
- 3. `machine_learning_I/features.md_3` | `machine_learning_I/features.md` | score=1.176
- 4. `machine_learning_II/introduction.md_0` | `machine_learning_II/introduction.md` | score=0.992
- 5. `high_throughput/data_mining.md_0` | `high_throughput/data_mining.md` | score=0.983

## PASS: `mace_question`

Query: `How does MACE differ from earlier machine learning potentials?`

Notes: ML potential method question.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `machine_learning_potentials/introduction.md_0` | `machine_learning_potentials/introduction.md` | score=1.645
- 2. `machine_learning_potentials/mlp.ipynb_0` | `machine_learning_potentials/mlp.ipynb` | score=1.643
- 3. `machine_learning_potentials/index.md_0` | `machine_learning_potentials/index.md` | score=1.641
- 4. `machine_learning_potentials/mlp.ipynb_3` | `machine_learning_potentials/mlp.ipynb` | score=1.591
- 5. `machine_learning_potentials/mace.md_2` | `machine_learning_potentials/mace.md` | score=1.547

## PASS: `pandas_question`

Query: `How do I use pandas for materials data?`

Notes: Practical/code-oriented database query.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `database/pandas.ipynb_0` | `database/pandas.ipynb` | score=0.966
- 2. `midterm_review/database.md_0` | `midterm_review/database.md` | score=0.916
- 3. `database/bulk_modulus.ipynb_4` | `database/bulk_modulus.ipynb` | score=0.804
- 4. `database/materials_database.md_2` | `database/materials_database.md` | score=0.787
- 5. `database/index.md_0` | `database/index.md` | score=0.741

## PASS: `crystal_structure`

Query: `What information defines a crystal structure?`

Notes: Multi-source structures concept query.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `structures/crystal_structure.ipynb_3` | `structures/crystal_structure.ipynb` | score=1.130
- 2. `structures/crystal_structure.ipynb_0` | `structures/crystal_structure.ipynb` | score=1.126
- 3. `structures/vesta.md_0` | `structures/vesta.md` | score=1.037
- 4. `structures/crystal_structure.ipynb_2` | `structures/crystal_structure.ipynb` | score=1.006
- 5. `structures/structure_formats.md_3` | `structures/structure_formats.md` | score=1.004

## PASS: `dft_question`

Query: `What is density functional theory used for?`

Notes: Exact acronym and full-name retrieval.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `high_throughput/codes.md_0` | `high_throughput/codes.md` | score=1.274
- 2. `models_and_theories_I/modelling.md_1` | `models_and_theories_I/modelling.md` | score=1.169
- 3. `models_and_theories_II/kmc.md_1` | `models_and_theories_II/kmc.md` | score=0.995
- 4. `machine_learning_potentials/training_validation.md_0` | `machine_learning_potentials/training_validation.md` | score=0.967
- 5. `models_and_theories_I/dft.md_1` | `models_and_theories_I/dft.md` | score=0.965

## PASS: `airss_question`

Query: `What is AIRSS for structure prediction?`

Notes: Tests newly included optimization file.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `optimization/airss.md_3` | `optimization/airss.md` | score=1.171
- 2. `optimization/airss.md_0` | `optimization/airss.md` | score=1.000
- 3. `high_throughput/introduction.md_1` | `high_throughput/introduction.md` | score=0.996
- 4. `optimization/airss.md_1` | `optimization/airss.md` | score=0.756
- 5. `optimization/airss.md_2` | `optimization/airss.md` | score=0.628

## PASS: `high_throughput_workflow`

Query: `What is a high-throughput workflow?`

Notes: Hyphenated wording should match normalized terms.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `high_throughput/workflow.md_5` | `high_throughput/workflow.md` | score=1.703
- 2. `high_throughput/workflow.md_0` | `high_throughput/workflow.md` | score=1.609
- 3. `final_review/high_throughput.md_0` | `final_review/high_throughput.md` | score=1.452
- 4. `high_throughput/codes.md_2` | `high_throughput/codes.md` | score=1.328
- 5. `high_throughput/workflow.md_4` | `high_throughput/workflow.md` | score=1.288

## PASS: `vanda_setup`

Query: `How do students get access to Vanda?`

Notes: Course setup/support query.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: True

Top results:
- 1. `orientation/vanda.md_0` | `orientation/vanda.md` | score=0.976
- 2. `orientation/vanda.md_1` | `orientation/vanda.md` | score=0.934
- 3. `orientation/orientation.md_0` | `orientation/orientation.md` | score=0.930
- 4. `orientation/setup.md_4` | `orientation/setup.md` | score=0.836
- 5. `orientation/vanda.md_3` | `orientation/vanda.md` | score=0.830

## XFAIL: `unknown_external`

Query: `What is the cafeteria menu today?`

Notes: Out-of-scope query; should have low confidence or no meaningful course match.

Checks:
- `expected_file_hit`: True
- `expected_term_hit`: True
- `temporal_context_hit`: True
- `weak_result_hit`: False

Top results:
- 1. `computer/hpc.md_6` | `computer/hpc.md` | score=0.721
- 2. `computer/history.md_1` | `computer/history.md` | score=0.716
- 3. `structures/vesta.md_1` | `structures/vesta.md` | score=0.691
- 4. `computer/hardware.md_0` | `computer/hardware.md` | score=0.659
- 5. `computer/hardware.md_4` | `computer/hardware.md` | score=0.652
