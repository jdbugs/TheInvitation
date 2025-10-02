from __future__ import annotations

import asyncio
import random
import unittest

from engine.aurora import WeaveResponse
from engine.observer import FeedbackSettings, ObserverSettings, ThresholdObserver


class StubComposer:
    def __init__(self) -> None:
        self.calls = []
        self.max_layers = 2
        self.architecture = "hybrid"

    async def compose(self, request):
        self.calls.append(request)
        text = f"[{request.channel}] {request.prompt or 'silence'}"
        return WeaveResponse(text=text, blueprint={"channel": request.channel, "layers": []})

    def reconfigure(self, **updates):
        if "max_layers" in updates:
            self.max_layers = updates["max_layers"]
        if "architecture" in updates:
            self.architecture = updates["architecture"]


class StubDisplay:
    def __init__(self) -> None:
        self.emitted = []

    async def banner(self):
        return None

    async def emit(self, response):
        self.emitted.append(response.text)

    async def close(self):
        return None


class ObserverTests(unittest.TestCase):
    def test_silence_cancelled_when_new_input_arrives(self) -> None:
        composer = StubComposer()
        display = StubDisplay()

        async def scenario():
            settings = ObserverSettings(min_delay=0.01, max_delay=0.02, min_silence=0.2, max_silence=0.2)
            feedback = FeedbackSettings(target_length=20, tolerance=10, adjust_rate=0.2, architecture_shift=3)
            observer = ThresholdObserver(composer, display, settings=settings, feedback=feedback, rng=random.Random(0))
            await observer.handle_input("first")
            await asyncio.sleep(0.05)
            await observer.handle_input("second")
            await asyncio.sleep(0.05)
            await observer.aclose()
            await asyncio.sleep(0.05)

        asyncio.run(scenario())

        self.assertEqual(len(display.emitted), 2)
        self.assertTrue(all(text.startswith("[input]") for text in display.emitted))

