from __future__ import annotations

from pathlib import Path
import asyncio
import random
import tempfile
import unittest

from engine.configuration import FieldConfig, MetamorphosisConfig, WeaveConfig, ArchitectureConfig
from engine.constellation import MycelialConstellation
from engine.aurora import AuroraWeave, WeaveImpulse


class DummyOracle:
    def __init__(self) -> None:
        self.enabled = True
        self.prompts: list[str] = []

    async def dream(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "oracle whisper"


class AuroraTests(unittest.TestCase):
    def _constellation(self) -> MycelialConstellation:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            path.joinpath("invitation.txt").write_text("remember the threshold", encoding="utf-8")
            config = FieldConfig(clip=120, min_slices=1, max_slices=3, base_tags=("threshold",), mutation_rate=0.0)
            constellation = MycelialConstellation.from_data_dir(path, config)
        return constellation

    def test_compose_without_oracle(self) -> None:
        constellation = self._constellation()
        weave = AuroraWeave(
            constellation,
            config=WeaveConfig(
                max_chars=200,
                oracle_weight=0.0,
                entangle_bias=0.0,
                recursion_bias=0.0,
                default_architecture="lattice",
                architectures=(ArchitectureConfig("lattice", shard_layers=2, oracle_bias=0.0, echo_prompt=True),),
            ),
            metamorphosis=MetamorphosisConfig(window=3, chaos=0.0, reactivity=0.0),
            oracle=None,
            rng=random.Random(0),
        )
        impulse = WeaveImpulse(channel="input", utterance="hello", echoes=[], tags=["threshold"])
        response = asyncio.run(weave.compose(impulse))
        self.assertIn("you leave a trace", response.text)
        self.assertEqual(response.blueprint["architecture"], "lattice")

    def test_oracle_participation(self) -> None:
        constellation = self._constellation()
        oracle = DummyOracle()
        weave = AuroraWeave(
            constellation,
            config=WeaveConfig(
                max_chars=200,
                oracle_weight=1.0,
                entangle_bias=0.0,
                recursion_bias=0.0,
                default_architecture="oracle",
                architectures=(ArchitectureConfig("oracle", shard_layers=1, oracle_bias=1.0, echo_prompt=False),),
            ),
            metamorphosis=MetamorphosisConfig(window=3, chaos=0.0, reactivity=0.0),
            oracle=oracle,
            rng=random.Random(0),
        )
        impulse = WeaveImpulse(channel="input", utterance="", echoes=[], tags=[])
        response = asyncio.run(weave.compose(impulse))
        self.assertIn("oracle", response.text)
        self.assertTrue(response.blueprint["oracle"].startswith("oracle"[:6]))
        self.assertGreater(len(oracle.prompts), 0)

    def test_metabolise_shifts_architecture(self) -> None:
        constellation = self._constellation()
        weave = AuroraWeave(
            constellation,
            config=WeaveConfig(
                max_chars=200,
                oracle_weight=0.0,
                entangle_bias=0.0,
                recursion_bias=0.0,
                default_architecture="lattice",
                architectures=(
                    ArchitectureConfig("lattice", shard_layers=1, oracle_bias=0.0, echo_prompt=True),
                    ArchitectureConfig("dream", shard_layers=2, oracle_bias=0.2, echo_prompt=True),
                ),
            ),
            metamorphosis=MetamorphosisConfig(window=3, chaos=0.0, reactivity=0.0),
            rng=random.Random(0),
        )
        seen = {weave.active_architecture}
        for _ in range(5):
            weave.metabolise(length=400, target=120, tolerance=20, learning_rate=0.5, architecture_push=2)
            seen.add(weave.active_architecture)
        self.assertIn("dream", seen)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
