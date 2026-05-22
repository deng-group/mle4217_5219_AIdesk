#!/usr/bin/env python3
"""
Phase A: Knowledge Graph Construction for Materials Informatics Course

This script:
1. Analyzes course chunks to extract concepts
2. Builds a knowledge graph with nodes and edges
3. Defines prerequisite and related relationships
4. Links nodes to content chunks
5. Generates knowledge_graph.json
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Set
import re


class KnowledgeGraphBuilder:
    """Build knowledge graph from course content"""

    def __init__(self, chunks_path: str):
        self.chunks_path = Path(chunks_path)
        self.chunks = []
        self.concepts = defaultdict(list)  # concept -> list of chunks
        self.nodes = {}  # node_id -> node_data
        self.edges = []  # list of edges

    def load_chunks(self) -> None:
        """Load chunks from JSONL file"""
        print("📖 Loading chunks...")
        with open(self.chunks_path, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = json.loads(line)
                self.chunks.append(chunk)

                # Index concepts
                for concept in chunk.get('concepts', []):
                    self.concepts[concept].append(chunk['chunk_id'])

        print(f"✓ Loaded {len(self.chunks)} chunks")
        print(f"✓ Found {len(self.concepts)} unique concepts")

    def create_module_nodes(self) -> None:
        """Create nodes for each module (main topic area)"""
        module_metadata = {
            'root': {
                'title': 'Course Root',
                'description': 'Top-level course pages and repository materials',
                'level': 1,
                'type': 'module'
            },
            'orientation': {
                'title': 'Orientation',
                'description': 'Course introduction, setup, and basic concepts',
                'level': 1,
                'type': 'module'
            },
            'programming': {
                'title': 'Programming',
                'description': 'Python, NumPy, Matplotlib, and coding fundamentals',
                'level': 1,
                'type': 'module'
            },
            'computer': {
                'title': 'Computer and Computation',
                'description': 'Hardware, software, version control, and performance',
                'level': 1,
                'type': 'module'
            },
            'database': {
                'title': 'Database',
                'description': 'Materials databases, formats, and data management',
                'level': 1,
                'type': 'module'
            },
            'atomistic_structure': {
                'title': 'Atomistic Structures',
                'description': 'Crystal structures, symmetry, defects, and materials',
                'level': 1,
                'type': 'module'
            },
            'structures': {
                'title': 'Structures',
                'description': 'Crystal structures, symmetry, defects, interfaces, and materials structures',
                'level': 1,
                'type': 'module'
            },
            'midterm_review': {
                'title': 'Midterm Review',
                'description': 'Review material for the first part of the course',
                'level': 1,
                'type': 'module'
            },
            'models_and_theories_I': {
                'title': 'Models and Theories I',
                'description': 'Force fields, DFT, and atomic simulation',
                'level': 1,
                'type': 'module'
            },
            'models_and_theories_II': {
                'title': 'Models and Theories II',
                'description': 'Statistical mechanics, MD, and Monte Carlo',
                'level': 1,
                'type': 'module'
            },
            'optimization': {
                'title': 'Optimization',
                'description': 'Local and global optimization methods',
                'level': 1,
                'type': 'module'
            },
            'high_throughput': {
                'title': 'High Throughput Methods',
                'description': 'Workflow, data mining, and automation',
                'level': 1,
                'type': 'module'
            },
            'machine_learning_I': {
                'title': 'Machine Learning I',
                'description': 'Machine learning foundations, features, models, tasks, and validation',
                'level': 1,
                'type': 'module'
            },
            'machine_learning_II': {
                'title': 'Machine Learning II',
                'description': 'Advanced machine learning, graphs, GNNs, and diffusion models',
                'level': 1,
                'type': 'module'
            },
            'machine_learning_potentials': {
                'title': 'Machine Learning Potentials',
                'description': 'ML interatomic potentials and training',
                'level': 1,
                'type': 'module'
            },
            'final_review': {
                'title': 'Final Review',
                'description': 'Review material for the final part of the course',
                'level': 1,
                'type': 'module'
            },
            'figures': {
                'title': 'Figures',
                'description': 'Source notebooks and supporting materials for course figures',
                'level': 1,
                'type': 'module'
            }
        }

        module_ids = sorted({c.get('module', 'root') for c in self.chunks})

        for module_id in module_ids:
            metadata = module_metadata.get(module_id, {
                'title': module_id.replace('_', ' ').title(),
                'description': f"{module_id.replace('_', ' ').title()} course material",
                'level': 1,
                'type': 'module'
            })
            # Find chunks for this module
            module_chunks = [c['chunk_id'] for c in self.chunks if c.get('module') == module_id]

            node = {
                'node_id': module_id,
                'type': 'module',
                'title': metadata['title'],
                'description': metadata['description'],
                'level': metadata['level'],
                'chunks': module_chunks,
                'concepts': [],
                'metadata': {
                    'module': module_id,
                    'num_chunks': len(module_chunks)
                }
            }
            self.nodes[module_id] = node

    def create_topic_nodes(self) -> None:
        """Create nodes for individual topics/subsections"""
        topic_counter = Counter()

        for chunk in self.chunks:
            section = chunk.get('section', 'unknown')
            module = chunk.get('module', 'root')

            # Create a cleaner topic ID
            topic_id = f"{module}_{section}".replace('/', '_').replace(' ', '_').lower()

            if topic_id not in self.nodes:
                # Get title from headings
                title = chunk.get('title', section.replace('_', ' ').title())

                # Find related chunks
                related_chunks = [c['chunk_id'] for c in self.chunks
                               if c.get('module') == module and c.get('section') == section]

                node = {
                    'node_id': topic_id,
                    'type': 'topic',
                    'title': title,
                    'description': f"{title} - Part of {module}",
                    'level': 2,
                    'chunks': related_chunks,
                    'concepts': [],
                    'metadata': {
                        'module': module,
                        'section': section,
                        'num_chunks': len(related_chunks)
                    }
                }
                self.nodes[topic_id] = node

            # Add concepts to topic
            for concept in chunk.get('concepts', [])[:10]:  # Limit concepts
                if concept not in self.nodes[topic_id]['concepts']:
                    self.nodes[topic_id]['concepts'].append(concept)

    def create_concept_nodes(self) -> None:
        """Create nodes for key concepts"""
        # Filter concepts that appear in multiple chunks
        frequent_concepts = {c: chunks for c, chunks in self.concepts.items()
                           if len(chunks) >= 2}

        # Sort by frequency and take top concepts
        top_concepts = sorted(frequent_concepts.items(),
                            key=lambda x: len(x[1]),
                            reverse=True)[:200]

        concept_id = 0
        for concept, chunk_ids in top_concepts:
            # Clean concept name
            concept_clean = concept.strip('*').strip().strip('"').strip()
            if len(concept_clean) < 3:
                continue

            # Skip very generic terms
            generic_terms = {'example', 'figure', 'note', 'important', 'warning',
                          'definition', 'the', 'and', 'for', 'are', 'this', 'that'}
            if concept_clean.lower() in generic_terms:
                continue

            node_id = f"concept_{concept_id}"
            concept_id += 1

            node = {
                'node_id': node_id,
                'type': 'concept',
                'title': concept_clean,
                'description': f"Key concept: {concept_clean}",
                'level': 3,
                'chunks': chunk_ids,
                'concepts': [concept_clean],
                'metadata': {
                    'num_chunks': len(chunk_ids),
                    'concept': concept_clean
                }
            }
            self.nodes[node_id] = node

    def create_edges(self) -> None:
        """Create edges between nodes"""

        # Module hierarchy: root -> modules
        for node_id, node in self.nodes.items():
            if node['type'] == 'module':
                self.edges.append({
                    'source': 'root',
                    'target': node_id,
                    'type': 'hierarchy',
                    'weight': 1.0
                })

        # Topic hierarchy: module -> topics
        for node_id, node in self.nodes.items():
            if node['type'] == 'topic':
                module = node['metadata'].get('module', 'root')
                if module in self.nodes:
                    self.edges.append({
                        'source': module,
                        'target': node_id,
                        'type': 'hierarchy',
                        'weight': 1.0
                    })

        # Concept relationships: topic -> concepts
        concept_to_node = {}
        for node_id, node in self.nodes.items():
            if node['type'] == 'concept':
                concept = node['metadata'].get('concept', '').lower()
                concept_to_node[concept] = node_id

        for node_id, node in self.nodes.items():
            if node['type'] == 'topic':
                for concept in node['concepts']:
                    concept_lower = concept.lower()
                    if concept_lower in concept_to_node:
                        self.edges.append({
                            'source': node_id,
                            'target': concept_to_node[concept_lower],
                            'type': 'contains',
                            'weight': 0.8
                        })

        # Prerequisite relationships (based on module order)
        preferred_module_order = [
            'root',
            'orientation',
            'programming',
            'computer',
            'database',
            'structures',
            'atomistic_structure',
            'midterm_review',
            'models_and_theories_I',
            'models_and_theories_II',
            'optimization',
            'high_throughput',
            'machine_learning_I',
            'machine_learning_II',
            'machine_learning_potentials',
            'final_review',
            'figures'
        ]
        existing_modules = [node_id for node_id, node in self.nodes.items() if node['type'] == 'module']
        ordered_modules = [m for m in preferred_module_order if m in existing_modules]
        ordered_modules.extend(sorted(m for m in existing_modules if m not in ordered_modules))

        for i in range(len(ordered_modules) - 1):
            current = ordered_modules[i]
            next_module = ordered_modules[i + 1]
            if current in self.nodes and next_module in self.nodes:
                self.edges.append({
                    'source': current,
                    'target': next_module,
                    'type': 'prerequisite',
                    'weight': 0.9
                })

        # Related concepts based on shared chunks
        chunk_to_nodes = defaultdict(list)
        for node_id, node in self.nodes.items():
            for chunk_id in node.get('chunks', []):
                chunk_to_nodes[chunk_id].append(node_id)

        for chunk_id, node_ids in chunk_to_nodes.items():
            if len(node_ids) > 1:
                for i in range(len(node_ids)):
                    for j in range(i + 1, len(node_ids)):
                        # Check if edge already exists
                        exists = any(
                            (e['source'] == node_ids[i] and e['target'] == node_ids[j]) or
                            (e['source'] == node_ids[j] and e['target'] == node_ids[i])
                            for e in self.edges
                        )
                        if not exists:
                            self.edges.append({
                                'source': node_ids[i],
                                'target': node_ids[j],
                                'type': 'related',
                                'weight': 0.6
                            })

    def build(self) -> Dict[str, Any]:
        """Build the knowledge graph"""
        print("\n🔗 Building knowledge graph...")

        # Create root node
        self.nodes['root'] = {
            'node_id': 'root',
            'type': 'root',
            'title': 'Materials Informatics',
            'description': 'MLE4217/5219 Course',
            'level': 0,
            'chunks': [],
            'concepts': [],
            'metadata': {
                'course': 'Materials Informatics',
                'code': 'MLE4217/5219'
            }
        }

        self.create_module_nodes()
        print(f"✓ Created {len([n for n in self.nodes.values() if n['type'] == 'module'])} module nodes")

        self.create_topic_nodes()
        print(f"✓ Created {len([n for n in self.nodes.values() if n['type'] == 'topic'])} topic nodes")

        self.create_concept_nodes()
        print(f"✓ Created {len([n for n in self.nodes.values() if n['type'] == 'concept'])} concept nodes")

        self.create_edges()
        print(f"✓ Created {len(self.edges)} edges")

        return {
            'nodes': list(self.nodes.values()),
            'edges': self.edges,
            'metadata': {
                'num_nodes': len(self.nodes),
                'num_edges': len(self.edges),
                'num_modules': len([n for n in self.nodes.values() if n['type'] == 'module']),
                'num_topics': len([n for n in self.nodes.values() if n['type'] == 'topic']),
                'num_concepts': len([n for n in self.nodes.values() if n['type'] == 'concept'])
            }
        }

    def save(self, output_path: str) -> None:
        """Save knowledge graph to JSON file"""
        graph = self.build()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved knowledge graph to {output_path}")
        print(f"\n📊 Graph Statistics:")
        print(f"  - Total nodes: {graph['metadata']['num_nodes']}")
        print(f"  - Total edges: {graph['metadata']['num_edges']}")
        print(f"  - Modules: {graph['metadata']['num_modules']}")
        print(f"  - Topics: {graph['metadata']['num_topics']}")
        print(f"  - Concepts: {graph['metadata']['num_concepts']}")


def main():
    parser = argparse.ArgumentParser(description="Build a knowledge graph from Phase A chunks.")
    parser.add_argument("--chunks", default="data/phase_a/course_chunks.jsonl", help="Input chunks JSONL path.")
    parser.add_argument("--output", default="data/phase_a/knowledge_graph.json", help="Output graph JSON path.")
    args = parser.parse_args()

    chunks_path = args.chunks
    output_path = args.output

    print("📘 Phase A: Knowledge Graph Construction")
    print("=" * 50)

    builder = KnowledgeGraphBuilder(chunks_path)
    builder.load_chunks()
    builder.save(output_path)

    print("\n✓ Phase A complete!")


if __name__ == '__main__':
    main()
