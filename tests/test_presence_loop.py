"""Tests for the ambient presence loop behaviour."""
from __future__ import annotations

import asyncio
import time
import unittest

from engine.ambient_output import AmbientFragment, ComposeContext
from engine.echo_logic import EchoChamber
from engine.presence_loop import PresenceConfig, PresenceLoop


class StubComposer:
    """Minimal composer that records compose attempts."""

    def __init__(self) -> None:
        self.calls: list[ComposeContext] = []

    async def compose(self, context: ComposeContext) -> AmbientFragment:
        self.calls.append(context)
        return AmbientFragment(text="silence", source="stub", metadata={})


class StubDisplay:
    """Display double capturing rendered fragments."""

    def __init__(self) -> None:
        self.fragments: list[AmbientFragment] = []

    async def initialize(self) -> None:  # pragma: no cover - unused in tests
        return None

    async def shutdown(self) -> None:  # pragma: no cover - unused in tests
        return None

    async def render_fragment(self, fragment: AmbientFragment) -> None:
        self.fragments.append(fragment)

    async def emit_breath(self) -> None:  # pragma: no cover - unused in tests
        return None

    def capture_input(self) -> str:  # pragma: no cover - unused in tests
        return ""


class PresenceLoopSilenceCancellationTest(unittest.IsolatedAsyncioTestCase):
    async def test_silence_response_cancelled_by_fresh_input(self) -> None:
        composer = StubComposer()
        display = StubDisplay()
        echo = EchoChamber()
        config = PresenceConfig(
            min_delay=0.01,
            max_delay=0.01,
            silence_range=(0.2, 0.2),
            poll_interval=0.01,
            response_probability=0.0,
            breath_interval=(1000.0, 1000.0),
        )
        loop = PresenceLoop(composer, echo, display, tts=None, config=config)

        loop._next_breath = float("inf")  # prevent breath emissions during test
        loop._last_input = time.monotonic() - 10.0
        loop._silence_target = 0.0

        await loop._process_events()  # schedule silence response
        self.assertTrue(loop._silence_pending)

        await loop._input_queue.put("hello")
        await loop._process_events()  # process fresh input, cancelling silence
        self.assertFalse(loop._silence_pending)

        await asyncio.sleep(config.max_delay + 0.05)

        for task in list(loop._pending_tasks):
            await task

        self.assertEqual([], display.fragments)
        self.assertEqual([], composer.calls)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
