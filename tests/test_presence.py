import asyncio
import unittest

from engine.composer import Response
from engine.configuration import FeedbackConfig, TimingConfig
from engine.presence import LoopSettings, PresenceLoop


class StubComposer:
    def __init__(self) -> None:
        self.calls = []

    async def craft(self, *, user_text, channel):
        self.calls.append((user_text, channel))
        return Response(text="response", channel=channel, fragments=(), used_oracle=False)


class StubPortal:
    def __init__(self) -> None:
        self.emitted = []

    async def banner(self) -> None:
        return None

    async def emit(self, response: Response) -> None:
        self.emitted.append(response)

    def apply_surface(self, **_: object) -> None:
        pass


class PresenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_silence_task_cancels_on_new_input(self) -> None:
        composer = StubComposer()
        portal = StubPortal()
        loop = PresenceLoop(
            composer,
            portal,  # type: ignore[arg-type]
            LoopSettings(
                timing=TimingConfig(min_delay=0.0, max_delay=0.0, min_silence=5.0, max_silence=5.0, echo_memory=2),
                feedback=FeedbackConfig(target_chars=200, tolerance=50),
            ),
        )
        # Seed a silence task manually
        loop._silence_token = 1
        task = asyncio.create_task(loop._deliver_silence(0.05, token=1))
        await loop._handle_input("hello")
        loop._cancel_silence()
        await asyncio.sleep(0.1)
        self.assertEqual(len(portal.emitted), 1)
        self.assertEqual(portal.emitted[0].channel, "input")
        self.assertTrue(task.done())
        self.assertIsNone(task.result())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
