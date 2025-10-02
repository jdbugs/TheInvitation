"""Tests for the ambient output pipeline."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from engine.ambient_output import AmbientOutputEngine, ComposeContext
from engine.echo_logic import EchoChamber
from engine.seeds import SeedLibrary


class SeedLibraryChunkingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        data_dir = Path(self._tmp.name)
        very_long = "presence. " * 320
        (data_dir / "The_Invitation.txt").write_text(very_long, encoding="utf-8")
        (data_dir / "transcripts.txt").write_text(very_long, encoding="utf-8")
        journal_payload = json.dumps([
            {"text": " ".join(["surrender"] * 280)}
        ])
        (data_dir / "journals.json").write_text(journal_payload, encoding="utf-8")
        self.library = SeedLibrary(data_dir, max_words=50, max_chars=200)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_fragments_respect_bounds(self) -> None:
        for source, fragments in self.library.sources().items():
            self.assertTrue(fragments, f"expected fragments for {source}")
            for fragment in fragments:
                word_count = len(fragment.text.split())
                self.assertLessEqual(word_count, 50)
                self.assertLessEqual(len(fragment.text), 200)

    def test_tag_targeting_prefers_matches(self) -> None:
        targeted = self.library.sample("journal", tags=["surrender"], count=2)
        self.assertTrue(targeted)
        for fragment in targeted:
            self.assertIn("surrender", fragment.tags)


class AmbientOutputEngineComposeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        data_dir = Path(self._tmp.name)
        (data_dir / "The_Invitation.txt").write_text("stillness\n\nspace", encoding="utf-8")
        (data_dir / "transcripts.txt").write_text("echoing threshold", encoding="utf-8")
        (data_dir / "journals.json").write_text("[{\"text\": \"drift into surrender\"}]", encoding="utf-8")
        library = SeedLibrary(data_dir)
        echo = EchoChamber()
        self.engine = AmbientOutputEngine(data_dir, echo, llm=None, library=library)

    async def asyncTearDown(self) -> None:
        self._tmp.cleanup()

    async def test_compose_produces_concise_output(self) -> None:
        context = ComposeContext(reason="silence")
        fragment = await self.engine.compose(context)
        self.assertTrue(fragment.text.strip())
        paragraphs = [p for p in fragment.text.strip().split("\n\n") if p]
        self.assertLessEqual(len(paragraphs), 3)
        for paragraph in paragraphs:
            max_line = max(len(line) for line in paragraph.splitlines())
            self.assertLessEqual(max_line, 72)
            self.assertLessEqual(len(paragraph.split()), 90)
        self.assertIsNotNone(fragment.layers)
        if fragment.layers:
            self.assertLessEqual(len(fragment.layers), 3)
        self.assertTrue(fragment.signature)
        self.assertEqual(fragment.metadata.get("signature"), fragment.signature)
        self.assertIn("blueprint", fragment.metadata)

    async def test_user_trace_is_trimmed(self) -> None:
        echoing_text = " ".join(["word"] * 160)
        context = ComposeContext(reason="input", user_input=echoing_text)
        fragment = await self.engine.compose(context)
        self.assertLessEqual(len(fragment.text.split()), 120)
        self.assertIsNotNone(fragment.layers)
        if fragment.layers:
            first_layer = fragment.layers[0]
            self.assertLessEqual(len(first_layer.split()), 40)

    async def test_blueprint_shifts_with_reason(self) -> None:
        silence = await self.engine.compose(ComposeContext(reason="silence"))
        loop = await self.engine.compose(ComposeContext(reason="recursive", user_input="repeat repeat repeat"))
        self.assertNotEqual(silence.metadata.get("blueprint"), loop.metadata.get("blueprint"))
        self.assertNotEqual(silence.signature, loop.signature)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
