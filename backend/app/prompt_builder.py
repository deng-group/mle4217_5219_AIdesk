#!/usr/bin/env python3
"""Build LLM prompt packages from query pipeline output.

This module does not call an LLM. It prepares the prompt, evidence, and policy
that a later answer-generation layer can send to a model.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.query_pipeline import QueryPipeline


SYSTEM_INSTRUCTION = """You are the course helper for the MLE4217/5219 Materials Informatics course.
Answer students using only the provided course evidence and optional short-memory context.
If evidence is insufficient, ambiguous, outdated, or out of scope, say so clearly.
Do not invent citations, facts, deadlines, course policies, or code behavior.
Do not show raw internal chunk IDs to students.
Start each generated answer with a natural location sentence, for example: "You can find this in [Title] ([file_path])." If multiple sources are genuinely needed, mention at most the top 3 in that first sentence. Do not use report-style headings such as "Relevant Course Source(s)".
Use readable Markdown formatting. Put the location sentence in its own first paragraph. After a blank line, answer procedural or workflow questions as a numbered list. For conceptual questions, use short paragraphs or bullets when that improves readability.
Prefer concise, instructional answers that help students understand the concept.
"""


STATUS_POLICIES = {
    "answerable": {
        "llm_action": "generate_answer",
        "instruction": "Answer the question using only the provided evidence. Start with a natural location sentence such as: \"You can find this in [Title] ([file_path]).\" If multiple sources are genuinely needed, mention at most the top 3 sources in that first sentence. Put that location sentence in its own first paragraph, followed by a blank line. For procedural or workflow questions, answer with a concise numbered list. Do not use report-style headings. Do not show raw chunk IDs. Cite sources by title and file path only.",
    },
    "needs_time_context": {
        "llm_action": "generate_answer",
        "instruction": "Answer using only the provided evidence and explicitly state the academic year/semester. Start with a natural location sentence such as: \"For AY2025/2026 Semester 2, you can find this in [Title] ([file_path]).\" If multiple sources are genuinely needed, mention at most the top 3 sources in that first sentence. Put that location sentence in its own first paragraph, followed by a blank line. For procedural or workflow questions, answer with a concise numbered list. Do not present offering-specific logistics as timeless. Do not use report-style headings. Do not show raw chunk IDs. Cite sources by title and file path only.",
    },
    "needs_clarification": {
        "llm_action": "ask_clarification",
        "instruction": "Do not answer broadly. Ask the student to narrow the question to a concept, module, task, or comparison.",
    },
    "weak_evidence": {
        "llm_action": "insufficient_evidence",
        "instruction": "Do not answer as if verified. Explain that the course evidence is insufficient and suggest a more specific question.",
    },
    "out_of_scope": {
        "llm_action": "refuse_or_fallback",
        "instruction": "Do not answer from course knowledge. Explain that the question appears outside the course scope. Web fallback may be considered later if enabled.",
    },
}


class PromptBuilder:
    """Construct structured prompt packages for future LLM calls."""

    def __init__(
        self,
        max_evidence: int | None = None,
        max_memory_turns: int = 4,
        evidence_score_threshold: float = 0.60,
    ):
        self.max_evidence = max_evidence
        self.max_memory_turns = max_memory_turns
        self.evidence_score_threshold = evidence_score_threshold

    def build(self, pipeline_result: dict, short_memory: list[dict] | None = None) -> dict:
        status = pipeline_result["status"]
        policy = STATUS_POLICIES.get(status, STATUS_POLICIES["weak_evidence"])
        memory = self._trim_memory(short_memory or [])
        evidence = self._select_evidence(pipeline_result)

        prompt_sections = [
            f"System instruction:\n{SYSTEM_INSTRUCTION.strip()}",
            f"Answerability status: {status}",
            f"Required action: {policy['llm_action']}",
            f"Policy:\n{policy['instruction']}",
        ]

        if pipeline_result.get("temporal_context"):
            prompt_sections.append(f"Temporal context: {pipeline_result['temporal_context']}")

        if memory:
            prompt_sections.append("Short memory from this open session:\n" + self._format_memory(memory))

        if policy["llm_action"] == "generate_answer":
            prompt_sections.append("Evidence:\n" + self._format_evidence(evidence))
        else:
            prompt_sections.append("Retrieved evidence summary:\n" + self._format_evidence(evidence))

        prompt_sections.append(f"Student question:\n{pipeline_result['query']}")

        return {
            "query": pipeline_result["query"],
            "status": status,
            "llm_action": policy["llm_action"],
            "answer_policy": {
                "use_only_evidence": policy["llm_action"] == "generate_answer",
                "cite_sources": policy["llm_action"] == "generate_answer",
                "requires_temporal_context": pipeline_result.get("needs_temporal_context", False),
                "temporal_context": pipeline_result.get("temporal_context"),
                "evidence_score_threshold": self.evidence_score_threshold,
                "short_memory_scope": "current_window_only",
                "memory_persistence": "cleared_when_window_or_session_closes",
            },
            "short_memory": memory,
            "evidence": evidence,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION.strip()},
                {"role": "user", "content": "\n\n".join(prompt_sections[1:])},
            ],
            "final_prompt": "\n\n---\n\n".join(prompt_sections),
        }

    def _select_evidence(self, pipeline_result: dict) -> list[dict]:
        selected = []
        evidence = [
            item
            for item in pipeline_result.get("evidence", [])
            if item["score"] >= self.evidence_score_threshold or item.get("temporal_context")
        ]
        if not evidence and pipeline_result.get("evidence"):
            evidence = [pipeline_result["evidence"][0]]
        if self.max_evidence is not None:
            evidence = evidence[: self.max_evidence]

        for item in evidence:
            selected.append(
                {
                    "chunk_id": item["chunk_id"],
                    "file_path": item["file_path"],
                    "title": item["title"],
                    "score": item["score"],
                    "time_sensitive": item["time_sensitive"],
                    "temporal_context": item["temporal_context"],
                    "content": item["content"],
                }
            )
        return selected

    def _trim_memory(self, memory: list[dict]) -> list[dict]:
        allowed = []
        for item in memory[-self.max_memory_turns :]:
            role = item.get("role")
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                allowed.append({"role": role, "content": content[:1200]})
        return allowed

    @staticmethod
    def _format_memory(memory: list[dict]) -> str:
        return "\n".join(f"- {item['role']}: {item['content']}" for item in memory)

    @staticmethod
    def _format_evidence(evidence: list[dict]) -> str:
        if not evidence:
            return "- No evidence selected."
        lines = []
        for idx, item in enumerate(evidence, start=1):
            temporal = ""
            if item.get("temporal_context"):
                temporal = f" | temporal_context={item['temporal_context'].get('year')}"
            lines.append(
                f"[Source {idx}] title={item['title']} | file={item['file_path']} | "
                f"score={item['score']:.3f}{temporal}\n{item['content']}"
            )
        return "\n\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an LLM prompt package for a query.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-evidence", type=int, default=None)
    parser.add_argument("--evidence-threshold", type=float, default=0.60)
    parser.add_argument("--memory-json", type=Path, default=None, help="Optional JSON file containing [{'role','content'}] short-memory items.")
    args = parser.parse_args()

    memory = []
    if args.memory_json:
        memory = json.loads(args.memory_json.read_text(encoding="utf-8"))

    pipeline = QueryPipeline(top_k=args.top_k)
    builder = PromptBuilder(max_evidence=args.max_evidence, evidence_score_threshold=args.evidence_threshold)
    package = builder.build(pipeline.ask(args.query, short_memory=memory), short_memory=memory)
    print(json.dumps(package, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
