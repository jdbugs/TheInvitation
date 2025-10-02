from __future__ import annotations

import asyncio
import random
import unittest

from engine.aurora import AuroraWeave, WeaveRequest
from engine.constellation import ConstellationAtlas, Shard


class DummyAtlas(ConstellationAtlas):
    def __init__(self) -> None:
        shards = [
            Shard("This is a deliberately crafted shard with enough meaning to matter.", "journal", ("memory",)),
            Shard("The hush between the lines is also a kind of answer.", "invitation", ("stillness",)),
            Shard("You asked where the self dissolves; I reply with quiet.", "transcript", ("echo",)),
        ]
        super().__init__(shards, rng=random.Random(0))


class AuroraTests(unittest.TestCase):
    def test_weave_concise_response(self) -> None:
        atlas = DummyAtlas()
        weave = AuroraWeave(atlas, max_layers=3, max_chars=240, rng=random.Random(1))
        request = WeaveRequest(channel="input", prompt="tell me something", echoes=["prev"], tags=["memory"])

        async def run() -> str:
            response = await weave.compose(request)
            self.assertLessEqual(len(response.text), 240)
            self.assertIn("you offered", response.text)
            self.assertEqual(response.blueprint["channel"], "input")
            self.assertLessEqual(len(response.blueprint["layers"]), 3)
            return response.text

        asyncio.run(run())

    def test_silence_prefers_stillness(self) -> None:
        atlas = DummyAtlas()
        weave = AuroraWeave(atlas, max_layers=2, rng=random.Random(2))

        async def run() -> str:
            response = await weave.compose(WeaveRequest(channel="silence", prompt=None, echoes=[]))
            self.assertEqual(response.blueprint["channel"], "silence")
            self.assertTrue("remember:" in response.text or "trace:" in response.text)
            return response.text

        asyncio.run(run())

