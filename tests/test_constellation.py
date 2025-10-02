from __future__ import annotations

from pathlib import Path
import random
import tempfile
import unittest

from engine.constellation import ConstellationAtlas


class ConstellationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, name: str, content: str) -> None:
        (self.data_dir / name).write_text(content, encoding="utf-8")

    def test_atlas_clips_and_filters(self) -> None:
        self._write("The_Invitation.txt", "one\n\nTwo\n\nThis is a slightly longer fragment that should survive.")
        self._write("transcripts.txt", "User: hi\nSystem: welcome\n")
        self._write("journals.json", '[{"text": "short"}, {"text": "This is a journal entry with meaning."}]')
        atlas = ConstellationAtlas.from_data_dir(self.data_dir, rng=random.Random(0))
        shards = atlas.sample(limit=10)
        self.assertTrue(all(len(shard.text) <= 360 for shard in shards))
        texts = {shard.text for shard in shards}
        self.assertNotIn("short", texts)
        self.assertTrue(any(shard.source == "journal" for shard in shards))

    def test_describe_returns_preview(self) -> None:
        self._write("The_Invitation.txt", "A fragment with enough words to pass the gate.")
        self._write("transcripts.txt", "System: hello\nUser: hi there this should certainly be long enough\n")
        self._write("journals.json", '[{"text": "Another fragment with sufficient depth and warmth."}]')
        atlas = ConstellationAtlas.from_data_dir(self.data_dir, rng=random.Random(1))
        preview = atlas.describe(limit=2)
        self.assertGreaterEqual(len(preview), 1)
        self.assertLessEqual(len(preview), 2)
        self.assertTrue(all(preview))

