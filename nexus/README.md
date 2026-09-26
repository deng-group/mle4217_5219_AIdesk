# Nexus

Nexus is the standalone graph-based course explorer for MLE4217/5219. It
reuses this repository's RAG pipeline while remaining independent from the
Jupyter Book course website.

## Open the local test website

From the repository root, run:

```bash
./scripts/start_nexus_test.sh
```

The launcher performs the complete local preflight:

1. loads the ignored local configuration from `scripts/api_env.sh`;
2. finds a Python environment with the RAG dependencies;
3. makes a small real request to verify the API key, endpoint, and model;
4. starts Nexus at `http://127.0.0.1:5057/`; and
5. opens the test page in the default browser.

Keep the terminal open while testing. Press `Ctrl+C` to stop the local server.
To start the server without opening a browser, use:

```bash
./scripts/start_nexus_test.sh --no-browser
```

If `scripts/api_env.sh` does not exist, create it once:

```bash
cp scripts/api_env.example.sh scripts/api_env.sh
```

Then edit only the local `scripts/api_env.sh` and add the API token. The file is
ignored by Git and must never be committed.

To check the API without starting the website:

```bash
source scripts/api_env.sh
python3 scripts/check_nexus_api.py
```

A successful check prints the provider and model but never prints the token.

## Student-facing graph model

The interface presents two node levels:

1. `Chapter` — a primary course area such as Structures or Database.
2. `Concept` — a student-facing idea, method, tool, or section-level subject.

The source graph still retains `topic` and `keyword` provenance internally so
retrieval and future concept curation remain possible. Both are displayed as
Concept nodes in the interface.

Connections are evidence-backed and semantically neutral. A connection means
that two nodes are related in the supplied course materials; the RAG agent
explains the relationship only when the retrieved evidence supports it.

## Rebuild and validate the graph

From the repository root:

```bash
python3 nexus/graph/build_graph.py
python3 nexus/graph/validate_graph.py
```

The builder is deterministic: the same course chunks and taxonomy produce the
same node IDs, edges, and ordering.

## Important local files

- `nexus/app.py` — local Nexus server and RAG API.
- `nexus/dist/` — browser interface.
- `nexus/data/course_graph.json` — generated graph data.
- `nexus/PROJECT_PLAN.md` — product plan, status, and TODO items.
- `scripts/api_env.sh` — ignored local API configuration.
- `scripts/check_nexus_api.py` — safe live API preflight.
- `scripts/start_nexus_test.sh` — one-command local launcher.
