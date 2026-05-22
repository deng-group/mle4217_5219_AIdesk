# Phase A Deliverables: Knowledge Engineering

## Overview

This document describes the deliverables from Phase A of the AI-Powered Knowledge Graph Tutor project for the Materials Informatics course (MLE4217/5219).

## Course Structure

The course is built with **MyST** (Markedly Structured Text) and hosted at:
- Website: https://mle4217-5219.matsci.dev/
- Repository: https://github.com/deng-group/MLE4217_5219_book

### Content Modules

The course consists of 10 main modules:

1. **Orientation** - Course introduction, setup, and basic concepts
2. **Programming** - Python, NumPy, Matplotlib, and coding fundamentals
3. **Computer and Computation** - Hardware, software, version control, and performance
4. **Database** - Materials databases, formats, and data management
5. **Atomistic Structures** - Crystal structures, symmetry, defects, and materials
6. **Models and Theories I** - Force fields, DFT, and atomic simulation
7. **Models and Theories II** - Statistical mechanics, MD, and Monte Carlo
8. **Optimization** - Local and global optimization methods
9. **High Throughput Methods** - Workflow, data mining, and automation
10. **Machine Learning Potentials** - ML interatomic potentials and training

## Deliverables

### 1. course_chunks.jsonl

**Description**: A JSONL (JSON Lines) file containing 301 chunks of course content, each with associated metadata.

**Structure**:
```json
{
  "chunk_id": "unique_identifier",
  "content": "text content",
  "token_estimate": 200,
  "file_path": "path/to/file.md",
  "file_type": "markdown|notebook",
  "module": "module_name",
  "section": "section_name",
  "title": "Section Title",
  "headings": [
    {"level": 1, "title": "Heading", "position": 0}
  ],
  "concepts": ["concept1", "concept2"],
  "code_blocks": ["code1"]
}
```

**Fields**:
- `chunk_id`: Unique identifier (format: `{filename}_{chunk_number}`)
- `content`: The actual text content (200-400 tokens per chunk)
- `token_estimate`: Approximate token count
- `file_path`: Relative path to source file
- `file_type`: Either "markdown" or "notebook"
- `module`: Main module (e.g., "orientation", "programming")
- `section`: Subsection within the module
- `title`: Extracted from the first heading
- `headings`: Hierarchical heading structure
- `concepts`: Extracted key concepts (max 20)
- `code_blocks`: Code snippets (for notebooks or markdown with code)

**Chunking Strategy**:
- Target size: 200 tokens (approximately 150 words)
- Range: 100-400 tokens
- Split by headings first to preserve context
- Further split by paragraphs within sections
- Preserve code blocks as complete units

**Total Chunks**: 301

### 2. knowledge_graph.json

**Description**: A knowledge graph representing the course structure and concept relationships.

**Structure**:
```json
{
  "nodes": [
    {
      "node_id": "unique_id",
      "type": "root|module|topic|concept",
      "title": "Node Title",
      "description": "Description",
      "level": 0|1|2|3,
      "chunks": ["chunk_id1", "chunk_id2"],
      "concepts": ["concept1"],
      "metadata": {...}
    }
  ],
  "edges": [
    {
      "source": "node_id_1",
      "target": "node_id_2",
      "type": "hierarchy|prerequisite|contains|related",
      "weight": 0.0-1.0
    }
  ],
  "metadata": {
    "num_nodes": 289,
    "num_edges": 1616
  }
}
```

**Node Types**:
1. **Root** (1 node): Course overview
2. **Module** (10 nodes): Main topic areas
3. **Topic** (80 nodes): Individual subsections
4. **Concept** (198 nodes): Key concepts extracted from content

**Edge Types**:
1. **hierarchy**: Structural relationships (parent-child)
2. **prerequisite**: Learning dependencies based on module order
3. **contains**: Topic-concept relationships
4. **related**: Concepts that appear in the same chunks

**Graph Statistics**:
- Total nodes: 289
- Total edges: 1,616
- Average degree: ~11 connections per node

## Graph Structure

### Hierarchy

```
root (Materials Informatics)
├── orientation
│   ├── orientation
│   ├── introduction
│   ├── vanda
│   ├── setup
│   ├── jupyter
│   └── setup_local
├── programming
│   ├── github
│   ├── python_introduction
│   ├── numpy
│   ├── matplotlib
│   └── ai
├── computer
│   ├── git_examples
│   ├── software
│   ├── hardware
│   ├── history
│   ├── performance
│   ├── hpc
│   └── scaling
├── database
│   ├── database
│   ├── concepts
│   ├── formats
│   ├── materials_database
│   ├── pandas
│   ├── materials_project
│   └── bulk_modulus
├── atomistic_structure
│   ├── unit_cell
│   ├── symmetry
│   ├── prototypes
│   ├── reciprocal_space
│   ├── structure_formats
│   ├── crystal_structure
│   ├── site_properties
│   ├── molecule
│   ├── noncrystalline_materials
│   ├── defect
│   ├── interface
│   ├── advanced_structure
│   └── vesta
├── models_and_theories_I
│   ├── modelling
│   ├── force_fields
│   ├── dft
│   └── ase
├── models_and_theories_II
│   ├── statistical_mech
│   ├── molecular_dynamics
│   ├── monte_carlo
│   ├── kmc
│   └── md_mc
├── optimization
│   ├── introduction
│   ├── local_optimization
│   ├── global_optimization
│   ├── choose_opt
│   ├── transition_state
│   └── optimization
├── high_throughput
│   ├── introduction
│   ├── workflow
│   ├── data_mining
│   ├── thermodynamics
│   ├── codes
│   └── high_throughput
└── machine_learning_potentials
    ├── introduction
    ├── explicit
    ├── bp_nn
    ├── mace
    ├── umlp
    ├── training_validation
    ├── challenges
    └── mlp
```

## Tagging Rules

### Concept Extraction

Concepts are extracted using the following rules:

1. **Bold Text**: Terms marked with `**term**` in markdown
2. **Definitions**: Content within `{admonition}` blocks with `:class: info`
3. **Inline Code**: Technical terms in backticks (maximum 3 words)
4. **Headings**: Section titles (especially h3 and below)

**Filtering Rules**:
- Minimum length: 3 characters
- Maximum 20 concepts per chunk
- Generic terms excluded: "example", "figure", "note", "important", "warning", etc.
- Duplicates removed within each chunk

### Metadata Extraction

**Module Classification**:
- Determined by the first directory level in the file path
- Special case: files in root directory are classified as "root"

**Section Classification**:
- Determined by the second directory level or filename
- Used to group related chunks into topics

**Headings**:
- Extracted using regex pattern: `^(#{1,6})\s+(.+)$`
- Level indicates hierarchy (1-6)
- Position recorded for context

### Code Blocks

Extracted from:
1. Markdown code fences: ` ```python ... ``` `
2. Jupyter notebook code cells
3. Stored as complete units (not split)

## Prerequisite Relationships

Prerequisite relationships are inferred from:

1. **Module Order**: The course progression suggests dependencies
   - orientation → programming → computer → database → atomistic_structure → models_and_theories_I → models_and_theories_II → optimization → high_throughput → machine_learning_potentials

2. **Topic Dependencies**: Within modules, earlier topics may be prerequisites for later ones

3. **Concept Co-occurrence**: Concepts appearing together in multiple chunks are marked as related

## Usage Examples

### Querying Chunks

```python
import json

# Load chunks
chunks = []
with open('data/phase_a/course_chunks.jsonl', 'r') as f:
    for line in f:
        chunks.append(json.loads(line))

# Filter by module
python_chunks = [c for c in chunks if c['module'] == 'programming']

# Filter by concept
materials_db_chunks = [c for c in chunks if 'materials database' in c.get('concepts', [])]
```

### Querying Knowledge Graph

```python
import json

# Load graph
with open('data/phase_a/knowledge_graph.json', 'r') as f:
    graph = json.load(f)

# Get all modules
modules = [n for n in graph['nodes'] if n['type'] == 'module']

# Get prerequisites for a node
node_id = 'atomistic_structure'
prerequisites = [
    e for e in graph['edges']
    if e['target'] == node_id and e['type'] == 'prerequisite'
]

# Get related concepts
related = [
    e for e in graph['edges']
    if (e['source'] == node_id or e['target'] == node_id) and e['type'] == 'related'
]
```

## File Locations

All deliverables are located in: `data/phase_a/`

- `course_chunks.jsonl` - Chunked content with metadata
- `knowledge_graph.json` - Knowledge graph with nodes and edges
- `PHASE_A_DOCUMENTATION.md` - This documentation file
- `PHASE_A_SUMMARY.md` - Summary and quick reference
- `extract_content.py` - Content extraction script
- `build_knowledge_graph.py` - Knowledge graph construction script

## Next Steps

For **Phase B - AI Backend (RAG + Web Search)**:

1. **Compute Embeddings**:
   - Use OpenAI API or local models (sentence-transformers)
   - Embed each chunk's content
   - Store embeddings with chunk metadata

2. **Vector Database**:
   - Set up Qdrant, FAISS, or Weaviate
   - Index embeddings for efficient similarity search
   - Link to knowledge graph for node-aware retrieval

3. **RAG Pipeline**:
   - Implement query embedding
   - Retrieve top-k relevant chunks
   - Generate answers with source citations
   - Integrate knowledge graph for context

4. **Routing Model**:
   - Classify questions into RAG-only, web-search-only, or hybrid
   - Use course concepts to determine routing
   - Fallback to web search for external concepts

## Validation

The Phase A deliverables have been validated to ensure:

✓ All 73 course files processed (61 markdown + 12 notebooks)
✓ 301 chunks created (average 200 tokens each)
✓ 289 nodes in knowledge graph
✓ 1,616 edges connecting nodes
✓ All chunks linked to at least one node
✓ Concepts extracted and indexed
✓ Metadata preserved throughout pipeline

---

**Generated**: January 20, 2026
**Course**: Materials Informatics (MLE4217/5219)
**Instructor**: Asst. Prof. Zeyu Deng
**Institution**: National University of Singapore
