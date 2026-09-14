from __future__ import annotations

import unittest

from backend.app.answer_generator import AnswerGenerator
from backend.app.prompt_builder import PromptBuilder


class FakePipeline:
    def ask(self, query: str, short_memory: list[dict] | None = None) -> dict:
        return {
            "query": query,
            "status": "answerable",
            "next_action": "build_prompt",
            "confidence": 0.91,
            "temporal_context": None,
            "needs_temporal_context": False,
            "evidence": [
                {
                    "chunk_id": "course:test:chunk-1",
                    "file_path": "structures/index.md",
                    "title": "Structures",
                    "score": 0.91,
                    "time_sensitive": False,
                    "temporal_context": None,
                    "content": "Crystal structures describe ordered arrangements of atoms.",
                }
            ],
        }


class FakeStreamingProvider:
    name = "fake"
    model = "fake-stream-model"

    def stream(self, prompt_package: dict):
        yield "See course:test:chunk-1. "
        yield "Atoms are arranged in a crystal structure."

    def generate(self, prompt_package: dict) -> dict:
        raise AssertionError("Streaming must not fall back to the buffered provider method.")


class AnswerStreamingTest(unittest.TestCase):
    def test_stream_has_start_deltas_and_done_without_buffered_fallback(self) -> None:
        generator = AnswerGenerator(
            pipeline=FakePipeline(),
            prompt_builder=PromptBuilder(),
            provider=FakeStreamingProvider(),
        )

        events = list(generator.stream_answer("What is a crystal structure?"))

        self.assertEqual([event["type"] for event in events], ["start", "delta", "delta", "done"])
        self.assertEqual(events[0]["model"], "fake-stream-model")
        self.assertNotIn("course:test:chunk-1", events[1]["text"])
        self.assertEqual(
            events[-1]["answer"],
            "See Structures (structures/index.md). Atoms are arranged in a crystal structure.",
        )


if __name__ == "__main__":
    unittest.main()
