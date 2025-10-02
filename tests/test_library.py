from pathlib import Path
import tempfile
import unittest

from engine.configuration import LibraryConfig
from engine.library import SeedLibrary


class SeedLibraryTests(unittest.TestCase):
    def test_harvests_and_clips_fragments(self) -> None:
        config = LibraryConfig(clip_chars=40, min_words=2, max_fragments=5)
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "sample.txt"
            data.write_text(
                "First fragment that is definitely long enough to be clipped.\n\n"
                "Short\n\n"
                "Second fragment with plenty of words to keep.",
                encoding="utf-8",
            )
            library = SeedLibrary.from_path(Path(tmp), config)
            picks = library.pick(3)
        self.assertEqual(len(picks), 2)  # second block is too short
        self.assertTrue(all(len(p.text) <= 40 for p in picks))
        self.assertTrue(any(p.text.endswith("…") for p in picks))

    def test_pick_respects_max_fragments(self) -> None:
        config = LibraryConfig(clip_chars=120, min_words=1, max_fragments=1)
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.txt").write_text("one two three", encoding="utf-8")
            Path(tmp, "b.txt").write_text("four five six", encoding="utf-8")
            library = SeedLibrary.from_path(Path(tmp), config)
            picks = library.pick(5)
        self.assertEqual(len(picks), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
