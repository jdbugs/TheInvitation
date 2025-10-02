from __future__ import annotations

import asyncio
import unittest

from engine.aurora import WeaveResponse
from engine.observer import FeedbackTuning, PulseSettings, WitnessObserver


class FakeWeave:
    def __init__(self, recursion_bias: float = 0.0) -> None:
        self.active_architecture = "lattice"
        self._entangle_bias = 0.0
        self._recursion_bias = recursion_bias
        self.records: list[str] = []
        self.metabolised: list[int] = []

    @property
    def entangle_bias(self) -> float:
        return self._entangle_bias

    @property
    def recursion_bias(self) -> float:
        return self._recursion_bias

    async def compose(self, impulse):
        self.records.append(impulse.channel)
        return WeaveResponse(
            text=f"{impulse.channel}:{impulse.utterance or ''}",
            blueprint={"channel": impulse.channel, "architecture": "lattice", "layers": [], "oracle": None},
        )

    def metabolise(self, *, length: int, **_: int) -> None:
        self.metabolised.append(length)

    def reconfigure(self, **kwargs):
        pass

    def set_constellation(self, constellation):
        pass


class FakeDisplay:
    def __init__(self) -> None:
        self.emissions: list[str] = []

    async def banner(self) -> None:
        return None

    async def emit(self, response: WeaveResponse) -> None:
        self.emissions.append(response.text)

    async def close(self) -> None:
        return None


class ObserverTests(unittest.IsolatedAsyncioTestCase):
    async def test_silence_cancellation(self) -> None:
        weave = FakeWeave()
        display = FakeDisplay()
        observer = WitnessObserver(
            weave,
            display,
            settings=PulseSettings(min_delay=0.05, max_delay=0.05, min_silence=0.3, max_silence=0.3, echo_memory=4),
            tuning=FeedbackTuning(
                target_chars=10,
                tolerance=2,
                learning_rate=0.1,
                architecture_push=2,
                max_layers_ceiling=4,
                min_layers_floor=1,
                delay_floor=0.05,
                delay_ceiling=1.0,
                silence_floor=0.1,
                silence_ceiling=1.0,
            ),
        )
        observer._schedule_silence()
        await asyncio.sleep(0.05)
        await observer.handle_input("hello")
        await asyncio.sleep(0.2)
        self.assertIn("input:hello", display.emissions)
        self.assertFalse(any(text.startswith("silence:") for text in display.emissions))

    async def test_recursive_trigger(self) -> None:
        weave = FakeWeave(recursion_bias=1.0)
        display = FakeDisplay()
        observer = WitnessObserver(
            weave,
            display,
            settings=PulseSettings(min_delay=0.01, max_delay=0.01, min_silence=0.2, max_silence=0.2, echo_memory=4),
            tuning=FeedbackTuning(
                target_chars=5,
                tolerance=2,
                learning_rate=0.1,
                architecture_push=2,
                max_layers_ceiling=4,
                min_layers_floor=1,
                delay_floor=0.01,
                delay_ceiling=1.0,
                silence_floor=0.1,
                silence_ceiling=1.0,
            ),
        )
        await observer.handle_input("hi")
        await asyncio.sleep(0.1)
        self.assertIn("input:hi", display.emissions)
        await asyncio.sleep(0.1)
        self.assertTrue(any(text.startswith("recursive:") for text in display.emissions))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
