#!/usr/bin/env python3
"""Phase C answer generation layer.

This module connects the query pipeline and prompt builder to a pluggable LLM
provider. The default provider is a dry-run provider so tests can run without
API keys or network access.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.prompt_builder import PromptBuilder
from backend.app.query_pipeline import QueryPipeline


DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs without overriding existing environment."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class LLMProvider(Protocol):
    """Provider interface used by AnswerGenerator."""

    name: str

    def generate(self, prompt_package: dict) -> dict:
        """Generate an answer from a prompt package."""


@dataclass
class DryRunProvider:
    """Deterministic provider for local testing.

    It does not pretend to be an LLM. It returns a compact, policy-aware preview
    that lets us verify routing, evidence selection, citations, temporal context,
    and short-memory packaging.
    """

    name: str = "dry_run"

    def generate(self, prompt_package: dict) -> dict:
        action = prompt_package["llm_action"]
        status = prompt_package["status"]
        evidence = prompt_package.get("evidence", [])
        citations = [item["chunk_id"] for item in evidence]

        if action == "generate_answer":
            lead = "Dry run answer preview: this question is ready for an LLM answer using the selected course evidence."
            if prompt_package["answer_policy"].get("requires_temporal_context"):
                lead += f" Temporal context required: {prompt_package['answer_policy']['temporal_context']}."
            if citations:
                lead += " Candidate citations: " + ", ".join(citations) + "."
        elif action == "ask_clarification":
            lead = "Dry run answer preview: ask the student to narrow the question before answering."
        elif action == "insufficient_evidence":
            lead = "Dry run answer preview: explain that the course evidence is insufficient for a verified answer."
        elif action == "refuse_or_fallback":
            lead = "Dry run answer preview: explain that the question appears outside the course scope."
        else:
            lead = f"Dry run answer preview: inspect status `{status}` before answering."

        return {
            "provider": self.name,
            "model": None,
            "answer": lead,
            "citations": citations,
            "raw_response": None,
        }


@dataclass
class OpenAIResponsesProvider:
    """Optional OpenAI Responses API provider.

    Requires the `openai` package and `OPENAI_API_KEY`. The model is read from
    `OPENAI_MODEL` or the constructor, so the project can choose a current model
    without changing code.
    """

    model: str | None = None
    name: str = "openai_responses"

    def generate(self, prompt_package: dict) -> dict:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI provider requires the `openai` Python package.") from exc

        model = self.model or os.environ.get("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("Set OPENAI_API_KEY before using the OpenAI provider.")
        if not model:
            raise RuntimeError("Set OPENAI_MODEL or pass a model before using the OpenAI provider.")

        messages = prompt_package["messages"]
        system_message = messages[0]["content"]
        user_message = messages[1]["content"]

        client = OpenAI()
        response = client.responses.create(
            model=model,
            instructions=system_message,
            input=user_message,
        )
        answer = getattr(response, "output_text", None) or str(response)
        return {
            "provider": self.name,
            "model": model,
            "answer": answer,
            "citations": [item["chunk_id"] for item in prompt_package.get("evidence", [])],
            "raw_response": response.model_dump() if hasattr(response, "model_dump") else None,
        }


@dataclass
class GeminiProvider:
    """Google Gemini REST provider using generateContent."""

    model: str | None = None
    name: str = "gemini"

    def generate(self, prompt_package: dict) -> dict:
        model = self.model or os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY or GOOGLE_API_KEY before using the Gemini provider.")

        messages = prompt_package["messages"]
        system_message = messages[0]["content"]
        user_message = messages[1]["content"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_message}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {
                "temperature": 0.2,
            },
        }
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API error {exc.code}: {body}") from exc

        answer = self._extract_text(raw)
        return {
            "provider": self.name,
            "model": model,
            "answer": answer,
            "citations": [item["chunk_id"] for item in prompt_package.get("evidence", [])],
            "raw_response": raw,
        }

    @staticmethod
    def _extract_text(raw: dict) -> str:
        parts = []
        for candidate in raw.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                text = part.get("text")
                if text:
                    parts.append(text)
        if parts:
            return "\n".join(parts).strip()
        return json.dumps(raw, ensure_ascii=False)


@dataclass
class AnthropicProvider:
    """Anthropic-compatible Messages API provider."""

    model: str | None = None
    name: str = "anthropic"

    def generate(self, prompt_package: dict) -> dict:
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
        token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
        model = self.model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        if not token:
            raise RuntimeError("Set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY before using the Anthropic provider.")

        messages = prompt_package["messages"]
        payload = {
            "model": model,
            "max_tokens": 2048,
            "temperature": 0.2,
            "system": messages[0]["content"],
            "messages": [
                {
                    "role": "user",
                    "content": messages[1]["content"],
                }
            ],
        }
        req = request.Request(
            f"{base_url}/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": token,
                "User-Agent": "mle4275-agent/0.1",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=90) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error {exc.code}: {body}") from exc

        answer = self._extract_text(raw)
        return {
            "provider": self.name,
            "model": model,
            "answer": answer,
            "citations": [item["chunk_id"] for item in prompt_package.get("evidence", [])],
            "raw_response": raw,
        }

    @staticmethod
    def _extract_text(raw: dict) -> str:
        parts = []
        for item in raw.get("content", []):
            text = item.get("text")
            if text:
                parts.append(text)
        if parts:
            return "\n".join(parts).strip()
        return json.dumps(raw, ensure_ascii=False)


class AnswerGenerator:
    """End-to-end Phase C interface for one student question."""

    def __init__(
        self,
        pipeline: QueryPipeline | None = None,
        prompt_builder: PromptBuilder | None = None,
        provider: LLMProvider | None = None,
    ):
        self.pipeline = pipeline or QueryPipeline()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.provider = provider or DryRunProvider()

    def answer(self, query: str, short_memory: list[dict] | None = None) -> dict:
        memory = short_memory or []
        pipeline_result = self.pipeline.ask(query, short_memory=memory)
        prompt_package = self.prompt_builder.build(pipeline_result, short_memory=memory)
        provider_result = self.provider.generate(prompt_package)
        sources = self._student_sources(prompt_package["evidence"])
        answer = self._hide_internal_chunk_ids(provider_result["answer"], prompt_package["evidence"])

        return {
            "query": query,
            "status": prompt_package["status"],
            "llm_action": prompt_package["llm_action"],
            "next_action": pipeline_result["next_action"],
            "answer": answer,
            "citations": provider_result["citations"],
            "sources": sources,
            "provider": provider_result["provider"],
            "model": provider_result["model"],
            "confidence": pipeline_result["confidence"],
            "temporal_context": pipeline_result["temporal_context"],
            "short_memory": prompt_package["short_memory"],
            "evidence": prompt_package["evidence"],
            "prompt_package": prompt_package,
            "raw_response": provider_result["raw_response"],
        }

    @staticmethod
    def _student_sources(evidence: list[dict]) -> list[dict]:
        sources = []
        seen = set()
        for item in evidence:
            key = (item["title"], item["file_path"])
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                {
                    "title": item["title"],
                    "file_path": item["file_path"],
                    "chunk_id": item["chunk_id"],
                    "score": item["score"],
                }
            )
        return sources

    @staticmethod
    def _hide_internal_chunk_ids(answer: str, evidence: list[dict]) -> str:
        cleaned = answer
        for item in evidence:
            replacement = f"{item['title']} ({item['file_path']})"
            cleaned = cleaned.replace(item["chunk_id"], replacement)
        cleaned = re.sub(r"\(\s*chunk_id\s*=\s*[^)]+\)", "", cleaned)
        cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
        return cleaned.strip()


def provider_from_name(name: str, model: str | None = None) -> LLMProvider:
    if name == "dry_run":
        return DryRunProvider()
    if name == "openai":
        return OpenAIResponsesProvider(model=model)
    if name == "gemini":
        return GeminiProvider(model=model)
    if name == "anthropic":
        return AnthropicProvider(model=model)
    raise ValueError(f"Unknown provider: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an answer package for one query.")
    parser.add_argument("query")
    parser.add_argument("--provider", choices=["dry_run", "openai", "gemini", "anthropic"], default="dry_run")
    parser.add_argument("--model", default=None)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-evidence", type=int, default=None)
    parser.add_argument("--evidence-threshold", type=float, default=0.60)
    parser.add_argument("--memory-json", type=Path, default=None)
    parser.add_argument("--include-prompt", action="store_true")
    args = parser.parse_args()

    load_env_file(args.env_file)

    memory = []
    if args.memory_json:
        memory = json.loads(args.memory_json.read_text(encoding="utf-8"))

    generator = AnswerGenerator(
        pipeline=QueryPipeline(top_k=args.top_k),
        prompt_builder=PromptBuilder(
            max_evidence=args.max_evidence,
            evidence_score_threshold=args.evidence_threshold,
        ),
        provider=provider_from_name(args.provider, model=args.model),
    )
    try:
        result = generator.answer(args.query, short_memory=memory)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": str(exc),
                    "provider": args.provider,
                    "model": args.model,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        raise SystemExit(1) from exc
    if not args.include_prompt:
        result.pop("prompt_package", None)
        result.pop("raw_response", None)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
