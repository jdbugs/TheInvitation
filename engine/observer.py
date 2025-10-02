"""Threshold observer — orchestrates timing and recursion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, Iterable, List, Optional
import asyncio
import logging
import random
from collections import deque

from .aurora import AuroraWeave, WeaveRequest, WeaveResponse

LOGGER = logging.getLogger("invitation.observer")


@dataclass
class ObserverSettings:
    min_delay: float = 12.0
    max_delay: float = 48.0
    min_silence: float = 45.0
    max_silence: float = 120.0
    echo_memory: int = 6


class ThresholdObserver:
    """Coordinates input, silence, and recursive breath."""

    def __init__(
        self,
        composer: AuroraWeave,
        display,
        *,
        settings: ObserverSettings | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._composer = composer
        self._display = display
        self._settings = settings or ObserverSettings()
        self._loop = loop or asyncio.get_event_loop()
        self._rng = rng or random.Random()
        self._pending: List[asyncio.Task] = []
        self._silence_token = 0
        self._silence_task: asyncio.Task | None = None
        self._echoes: Deque[str] = deque(maxlen=self._settings.echo_memory)
        self._running = False

    async def run(self) -> None:
        self._running = True
        LOGGER.info("threshold observer awake")
        await self._display.banner()
        self._schedule_silence()
        try:
            while self._running:
                text = await self._read_line()
                if text is None:
                    break
                await self.handle_input(text)
        finally:
            await self.aclose()

    async def handle_input(self, text: str) -> None:
        clean = text.strip()
        LOGGER.info("received %d chars", len(clean))
        self._cancel_silence()
        await self._plan(channel="input", payload=clean)
        self._schedule_silence()

    async def trigger_recursive(self) -> None:
        LOGGER.debug("triggering recursive echo")
        await self._plan(channel="recursive", payload="")

    async def aclose(self) -> None:
        self._running = False
        self._cancel_silence()
        for task in list(self._pending):
            task.cancel()
        self._pending.clear()
        await self._display.close()

    async def _read_line(self) -> Optional[str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, input)

    async def _plan(self, *, channel: str, payload: str) -> None:
        delay = self._rng.uniform(self._settings.min_delay, self._settings.max_delay)
        LOGGER.debug("planning %s in %.2fs", channel, delay)

        async def deliver(token: int | None = None) -> None:
            if channel == "silence" and token != self._silence_token:
                LOGGER.debug("stale silence skipped (token %s != %s)", token, self._silence_token)
                return
            await asyncio.sleep(delay)
            request = WeaveRequest(channel=channel, prompt=payload or None, echoes=list(self._echoes))
            response = await self._composer.compose(request)
            await self._display.emit(response)
            if response.text:
                self._echoes.append(response.text)

        token = self._silence_token if channel == "silence" else None
        task = self._loop.create_task(deliver(token))
        self._pending.append(task)
        task.add_done_callback(lambda t: self._pending.remove(t) if t in self._pending else None)

    def _schedule_silence(self) -> None:
        delay = self._rng.uniform(self._settings.min_silence, self._settings.max_silence)
        self._silence_token += 1
        token = self._silence_token
        LOGGER.debug("scheduling silence %s for %.2fs", token, delay)

        async def deliver() -> None:
            await asyncio.sleep(delay)
            await self._plan(channel="silence", payload="")

        if self._silence_task:
            self._silence_task.cancel()
        self._silence_task = self._loop.create_task(deliver())

    def _cancel_silence(self) -> None:
        self._silence_token += 1
        if self._silence_task:
            LOGGER.debug("cancelling silence %s", self._silence_token)
            self._silence_task.cancel()
            self._silence_task = None

