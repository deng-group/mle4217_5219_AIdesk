# Nexus: Interactive Course Knowledge Graph and AI Learning Agent

## 1. Executive Summary

Nexus is a standalone web application for MLE4217/5219 Materials Informatics. It presents the course as an interactive knowledge graph instead of a conventional chapter list. Students explore two student-facing levels—chapters and concepts—inspect connections across the curriculum, and receive course-grounded explanations from an AI learning agent.

Nexus lives in the existing RAG repository but remains independent from the Jupyter Book website. It reuses the course ingestion, retrieval, evidence checking, short-term conversation context, and configured model API that already exist in the repository. It does not require a fine-tuned model for the first implementation.

## 2. Product Goals

### 2.1 Make the curriculum explorable

- Present the course as a connected graph rather than a flat table of contents.
- Allow students to begin from any chapter or concept.
- Reveal detail progressively so the graph remains understandable instead of becoming a dense network.
- Help students see concepts that recur across different parts of the course.

### 2.2 Improve conceptual understanding

- Give students immediate, context-aware explanations of any selected chapter or concept.
- Support questions about connections among chapters and concepts without hard-coding one narrow interpretation of each connection.
- Use the selected graph node as retrieval context while keeping retrieved course evidence as the only factual basis for an answer.
- Show the course sources used for each answer.

### 2.3 Preserve trustworthy course grounding

- Answer only when the course evidence is sufficiently strong.
- State clearly when the available course material is insufficient.
- Refuse out-of-scope questions rather than improvising an answer.
- Keep model credentials and provider configuration on the server.
- Preserve short-term context only within the current browser session.

## 3. Intended Users and Primary Journey

The primary users are students studying MLE4217/5219. A typical journey is:

1. Open Nexus in a mixed overview of chapters and representative concepts.
2. Select **Chapter** in the legend to view all chapters without concept clutter.
3. Select a chapter to reveal all concepts associated with it while keeping every other chapter visible.
4. Notice which revealed concepts also connect to other chapters.
5. Select **Concept** in the legend to view concepts without chapter clutter.
6. Select a concept to reveal the chapters in which it appears.
7. Select **Explain** in the right-hand AI panel to request a course-grounded explanation of the selected node.
8. Ask contextual follow-up questions and inspect the cited course sources.

## 4. Knowledge Graph Model

### 4.1 Two student-facing node levels

The graph uses two visible node types:

| Node type | Purpose | Example |
| --- | --- | --- |
| Chapter | A major course area | Structures |
| Concept | A meaningful course idea, method, tool, or section-level subject | Crystal Structure, Materials Project, Convex Hull |

The current source data contains both topic records and keyword records. In the redesigned interface, both are presented as **Concept** nodes because the distinction is not sufficiently useful to students. Their original source type may remain as internal provenance for retrieval, ranking, and later taxonomy review, but it is not shown as a separate visual level.

Concept nodes are global wherever possible. If the same concept appears in several chapters, those materials should connect to one canonical concept node rather than creating separate chapter-specific copies. Duplicate or low-value concept candidates will be reviewed in a later curation phase; that review is intentionally deferred until the new interaction model is working.

### 4.2 Connections

The graph separates course structure from knowledge association:

- chapter–concept connections show where a concept appears in the course;
- concept–concept and chapter–chapter connections may show semantically neutral associations supported by shared course evidence;
- the existing internal `contains`, `covers`, and `mentions` records may be retained as evidence, but the interface does not require students to distinguish them;
- `sequence` records the teaching order of primary chapters. It does not claim that every earlier chapter is a strict prerequisite.
- `related` is an undirected, semantically neutral association supported by shared course evidence.

Nexus does not predefine relationships such as “trains,” “causes,” or “enables.” A connection only means that the nodes are related in the course materials. When a student asks why they are related, the RAG system retrieves the relevant evidence and explains the relationship in the context of that question.

### 4.3 Evidence and weighting

Each generated connection records evidence such as:

- supporting course chunk IDs;
- shared internal topic or keyword provenance;
- associated chapter IDs; and
- a numerical association strength.

The strength is used only for ranking and progressive display. It is not presented as a scientific confidence score.

### 4.4 Legend modes and focus states

The lower-left legend is an interactive view selector, not only a colour key.

| State | Visible nodes and connections |
| --- | --- |
| Overview | Chapters and a curated set of representative concepts. |
| Chapter mode | All chapter nodes only. |
| Chapter focus | All chapters remain visible; concepts associated with the selected chapter appear; each revealed concept also connects to any other relevant visible chapter. |
| Concept mode | All student-facing concept nodes only. |
| Concept focus | All concepts remain visible; chapter nodes associated with the selected concept appear and connect to it. |

Selecting **Chapter** or **Concept** in the legend enters the corresponding mode. Selecting the active legend item again returns to the mixed overview. Selecting a node enters a focus state without removing the other nodes at the same level. Non-relevant nodes and connections may be visually de-emphasised, but they should not disappear when their continued presence helps students understand shared concepts.

This reciprocal interaction makes cross-chapter concepts visible without rendering every possible connection at once.

## 5. User Interface

### 5.1 Desktop layout

The first viewport is a full-screen working surface:

- **Left side:** interactive course graph.
- **Right side:** persistent AI chat panel.
- **Top of graph:** concept search and graph controls.
- **Lower-left overlay:** details for the selected node.

The visual direction is a light, calm academic workspace designed for sustained classroom use. Restrained colour coding distinguishes the two node levels:

- blue for chapters;
- warm amber for concepts.

### 5.2 Graph interactions

- Select **Chapter** or **Concept** in the legend to filter the graph by level.
- Select a chapter to reveal its concepts while preserving all chapter nodes.
- Select a concept to reveal its connected chapters while preserving all concept nodes.
- Select any node to focus the graph and set the AI context without immediately calling the model.
- Select **Explain** in the right-hand panel when an explanation is wanted.
- Drag nodes to improve a local arrangement.
- Drag the canvas to pan.
- Use the mouse wheel or trackpad to zoom.
- Reset the graph to the mixed overview.
- Fit the active graph to the available canvas.
- Search all chapters, concepts, and concept aliases.
- Use keyboard activation for searchable and visible controls.

### 5.3 AI chat panel

The right-hand chat panel includes:

- a visible selected-node context chip;
- an **Explain** button that generates an explanation for the selected node on demand;
- suggested questions based on the selected node;
- streamed model responses;
- short session memory;
- an evidence status message; and
- a collapsible list of course sources.

Students do not choose the model provider or enter API keys. Those settings remain server-side.

Changing nodes should cancel or supersede an earlier unfinished explanation so that the panel always corresponds to the current selection. Merely selecting a node must not call the model.

### 5.4 Responsive behaviour

On narrower screens, the graph and chat become vertically stacked. The graph remains the first interaction surface, while the chat retains a sufficiently large reading and input area.

## 6. AI and RAG Behaviour

### 6.1 Retrieval inputs

Each question may include:

- the student's natural-language question;
- the selected graph node label and type;
- recent messages from the current browser session; and
- the existing hybrid retrieval index over course chunks.

The selected node helps focus retrieval but is not treated as evidence by itself.

Selecting **Explain** creates a structured explanation request for the current node. The request asks the learning agent to explain the node using the course materials and, when useful, relate it to the graph neighbours currently visible. The same answerability policy applies to requested explanations and student-written questions.

### 6.2 Answerability policy

The current evidence gate supports five outcomes:

| Status | Behaviour |
| --- | --- |
| `answerable` | Generate an answer from selected course evidence. |
| `needs_time_context` | Answer with the applicable academic year or semester. |
| `needs_clarification` | Ask the student to narrow the question. |
| `weak_evidence` | State that the answer is not known from the available course material. |
| `out_of_scope` | State that the question is outside the course scope. |

Weak-evidence and out-of-scope responses are returned through deterministic course policy instead of asking the language model to improvise a refusal.

### 6.3 Model usage

- Reuse the API provider and key already configured for the existing project.
- Do not expose the credential in frontend code, requests, logs, or graph data.
- Do not require model fine-tuning for the initial version.
- Keep temperature low and require evidence-grounded answers.
- Return course titles and file paths instead of internal chunk identifiers.

## 7. Technical Architecture

```text
Course files
    ↓
Existing extraction and chunking
    ↓
Course chunks ──────────────┬───────────────┐
    ↓                       ↓               ↓
Hybrid retrieval     Graph builder     Evidence gate
    ↓                       ↓               ↓
Prompt builder       course_graph.json      │
    ↓                       ↓               │
Configured LLM API     Nexus frontend ←─────┘
    ↓
Streamed answer + course sources
```

### 7.1 Frontend

- Standalone HTML, CSS, and JavaScript under `nexus/dist/`.
- SVG-based interactive graph rendering.
- No client-side model credentials.
- Session-scoped conversation memory.
- No dependency on the sibling Jupyter Book repository.

### 7.2 Nexus server

The standalone Nexus server:

- serves the frontend;
- serves the generated graph;
- validates graph context node IDs;
- resolves selected nodes to trusted labels;
- calls the existing RAG and answer generation layers; and
- streams newline-delimited answer events to the browser.

Primary routes:

| Route | Purpose |
| --- | --- |
| `/` | Nexus application |
| `/api/graph` | Generated course graph |
| `/api/health` | Local service and graph status |
| `/api/answer/stream` | Course-grounded streamed answers |

### 7.3 Graph generation

The graph builder uses:

- extracted course chunks;
- a reviewed canonical concept taxonomy;
- deterministic concept matching;
- evidence-based chapter–concept associations;
- internal provenance that maps existing topic and keyword records into the student-facing concept level; and
- structural validation before the graph is used by the frontend.

## 8. Repository Organisation

Current Nexus files are isolated under `nexus/`:

```text
nexus/
├── PROJECT_PLAN.md
├── README.md
├── app.py
├── data/
│   └── course_graph.json
├── dist/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── graph/
    ├── build_graph.py
    ├── concept_taxonomy.json
    └── validate_graph.py
```

A broader repository reorganisation should happen only after Nexus and the existing RAG tests run reliably together. A possible later structure is:

```text
rag/                 Existing extraction, retrieval, prompting, and evaluation
projects/widget/     Existing Jupyter Book chat widget
projects/nexus/      Nexus graph application
shared/              Stable shared contracts and utilities
```

The migration should be performed separately, with import paths, scripts, deployment files, and tests updated in one controlled change.

## 9. Delivery Phases

### Phase 1: Graph foundation

- Map the existing topic and keyword records into one student-facing concept level.
- Preserve source provenance internally so retrieval and later taxonomy review remain possible.
- Generate evidence-based, semantically neutral connections.
- Validate IDs, edge endpoints, evidence, and key expected links.

### Phase 2: Interactive graph

- Build the full-screen graph workspace.
- Turn the legend into accessible Chapter and Concept mode controls.
- Implement reciprocal focus behaviour: chapter → related concepts and concept → related chapters.
- Preserve all same-level nodes during focus so shared concepts remain understandable.
- Add search, pan, zoom, drag, reset, and fit controls.
- Add node details and responsive behaviour.

### Phase 3: Course-grounded chat

- Place the persistent chat panel on the right.
- Send selected-node context to retrieval.
- Provide an explicit **Explain** action for the selected node.
- Avoid model requests when students are only navigating the graph.
- Cancel or supersede stale requests when the selection changes quickly.
- Stream answers and show course sources.
- Preserve conservative refusal behaviour.

### Phase 4: Quality and evaluation

- Evaluate graph density and navigation clarity with students.
- Review and filter the concept set after the two-level interaction is stable.
- Merge duplicate concepts and remove low-value or overly generic candidates.
- Test representative concept and cross-chapter questions.
- Measure refusal accuracy for weak or out-of-scope questions.
- Measure response latency and source usefulness.
- Refine the concept taxonomy and visibility thresholds.

### Phase 5: Deployment and pilot

- Configure a production service for the frontend, graph, and RAG API.
- Keep model credentials server-side.
- Add appropriate monitoring and privacy-conscious usage analytics.
- Run a limited student pilot before wider course adoption.

## 10. Current Implementation Status

Completed:

- standalone `nexus/` project area;
- deterministic knowledge graph generation;
- graph validation;
- source graph data containing 16 chapter nodes, 110 topic records, and 94 global keyword records;
- evidence-backed neutral associations;
- interactive graph workspace;
- right-hand AI chat layout;
- graph search and an initial mixed-node exploration view;
- two-level Chapter/Concept rendering with internal topic and keyword provenance preserved;
- interactive legend filtering with Overview, Chapter, and Concept modes;
- reciprocal chapter-to-concept and concept-to-chapter focus behaviour;
- pan, zoom, drag, reset, and fit interactions;
- selected-node RAG context;
- on-demand course-grounded explanations through the selected-node **Explain** button;
- streamed answer interface and course source display; and
- deterministic weak-evidence and out-of-scope policy responses.

Implemented interaction redesign:

1. Present topic and keyword records as one student-facing **Concept** level.
2. Make the legend switch between Overview, Chapter, and Concept views.
3. Implement reciprocal focus states while retaining all nodes of the active base level.
4. Trigger a course-grounded explanation in the right-hand panel for every selected node.
5. Curate and reduce the concept set only after the new interaction model can be evaluated in use.

Remaining before a production pilot:

- concept taxonomy review and filtering;
- broader question and retrieval evaluation;
- deployment configuration;
- provider reliability and retry behaviour;
- accessibility review with keyboard-only and screen-reader testing; and
- student usability testing.

## 11. Acceptance Criteria for the First Usable Version

The first usable Nexus version is complete when:

1. Students see only two student-facing node levels: Chapter and Concept.
2. The legend can isolate all chapters or all concepts and can return to the mixed overview.
3. Selecting a chapter preserves every chapter, reveals its associated concepts, and shows which of those concepts connect to other chapters.
4. Selecting a concept preserves every concept and reveals its associated chapters.
5. Search can locate all student-facing graph nodes.
6. Selecting any node visibly sets the AI context without calling the model.
7. Selecting **Explain** starts a course-grounded explanation for the current node.
8. Requested explanations and follow-up answers show course sources.
9. Weak or out-of-scope questions do not receive invented answers.
10. The API key remains server-side.
11. The interface works at desktop and mobile breakpoints without horizontal clipping.
12. The generated graph passes structural validation.
13. The existing RAG workflow and tests continue to operate.

## 12. Near-Term TODO

### 12.1 Concept and topic curation

- Review the current topic and keyword inventories before treating them as the final student-facing concept set.
- Merge duplicate or near-duplicate concepts and standardise naming.
- Remove administrative, overly generic, and low-value nodes.
- Decide which section-level topics should remain visible and which should be internal retrieval metadata only.
- Create an instructor-reviewed visibility list and regenerate the graph from it.

### 12.2 Standalone answer style and examples

- Rewrite the prompt examples for Nexus as a standalone learning application rather than an assistant embedded in the course website.
- Avoid Markdown links to internal course paths in the answer body.
- Present useful source titles in the source drawer instead of inserting course-file links into every explanation.
- Remove unnecessary academic-year or semester boilerplate unless the student's question is genuinely time-sensitive.
- Prefer a direct explanation first, followed by supported cross-concept connections and a concise evidence note.
- Add representative answer examples for chapter explanations, concept explanations, connection questions, insufficient evidence, and out-of-scope questions.

## 13. Future Opportunities

Possible later extensions include:

- selecting two nodes and asking specifically about their connection;
- small embedded course code examples and visualisations;
- instructor-reviewed concept collections or learning paths;
- optional student bookmarks and local progress state;
- privacy-conscious navigation analytics; and
- reuse of the Nexus framework for other materials and AI courses.
