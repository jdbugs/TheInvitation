"""Tests for ambient output fragment sizing behaviour."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine.ambient_output import AmbientOutputEngine
from engine.echo_logic import EchoChamber


class AmbientOutputFragmentSizingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        data_dir = Path(self._tempdir.name)
        (data_dir / "The_Invitation.txt").write_text("seed", encoding="utf-8")
        (data_dir / "journals.json").write_text("[]", encoding="utf-8")
        (data_dir / "transcripts.txt").write_text("", encoding="utf-8")
        self.engine = AmbientOutputEngine(data_dir, EchoChamber())

    def tearDown(self) -> None:
        self._tempdir.cleanup()

    def test_split_long_paragraph_chunks_words(self) -> None:
        long_text = " ".join(["presence"] * 400)
        fragments = self.engine._split_into_fragments(long_text, source="journal")
        self.assertTrue(fragments)
        for fragment in fragments:
            words = fragment["text"].split()
            self.assertLessEqual(len(words), 80)
            self.assertLessEqual(len(fragment["text"]), 420)

    def test_clip_fragment_adds_ellipsis_when_truncated(self) -> None:
        long_text = " ".join(f"word{i}" for i in range(120))
        clipped = self.engine._clip_fragment(long_text, max_words=60, max_chars=200)
        self.assertLessEqual(len(clipped.split()), 60)
        self.assertTrue(clipped.endswith("…"))


if __name__ == "__main__":  # pragma: no cover - convenience
    unittest.main()
