from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from engine.configuration import FieldConfig
from engine.constellation import LuminousShard, MycelialConstellation


class ConstellationTests(unittest.TestCase):
    def test_loading_and_sampling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            path.joinpath("invitation.txt").write_text("stillness\n\nremember the hush", encoding="utf-8")
            config = FieldConfig(clip=40, min_slices=1, max_slices=3, base_tags=("stillness",), mutation_rate=0.0)
            field = MycelialConstellation.from_data_dir(path, config)
            shards = field.sample(["stillness"], limit=2)
            self.assertTrue(all(isinstance(shard, LuminousShard) for shard in shards))
            self.assertTrue(any("remember" in shard.text for shard in shards))
            self.assertLessEqual(max(len(shard.text) for shard in shards), 40)

    def test_mutation_swaps_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            path.joinpath("journal.txt").write_text("silence is a door", encoding="utf-8")
            config = FieldConfig(clip=60, min_slices=1, max_slices=2, base_tags=("threshold",), mutation_rate=1.0)
            field = MycelialConstellation.from_data_dir(path, config)
            shard = field.sample(["silence"], limit=1)[0]
            self.assertIn("threshold", shard.tags)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
