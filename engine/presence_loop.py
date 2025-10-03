from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional

import logging

LOGGER = logging.getLogger(__name__)


@dataclass
class PresenceEvent:
    """Represents something the ambient field wants to surface."""

    kind: str
    text: Optional[str] = None
    delay: float = 0.0
    moment: float = 0.0

    @property
    def is_exit(self) -> bool:
        return self.kind == "exit"


class PresenceLoop:
    """Coordinates user input with ambient breathing gaps."""

    def __init__(
        self,
        *,
        response_delay: tuple[float, float] = (12.0, 32.0),
        idle_breath: tuple[float, float] = (36.0, 78.0),
    ) -> None:
        self._response_delay = response_delay
        self._idle_breath = idle_breath
        self._queue: asyncio.Queue[PresenceEvent] = asyncio.Queue()
        self._stop = asyncio.Event()
        self._input_task: Optional[asyncio.Task[None]] = None
        self._breath_task: Optional[asyncio.Task[None]] = None
        self._next_idle = self._schedule_idle()

    async def __aenter__(self) -> "PresenceLoop":
        loop = asyncio.get_event_loop()
        self._input_task = loop.create_task(self._input_worker())
        self._breath_task = loop.create_task(self._breath_worker())
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        self._stop.set()
        tasks = [task for task in (self._input_task, self._breath_task) if task]
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:  # pragma: no cover - clean shutdown
                pass

    async def next_event(self) -> PresenceEvent:
        return await self._queue.get()

    async def _input_worker(self) -> None:
        loop = asyncio.get_event_loop()
        while not self._stop.is_set():
            try:
                text = await loop.run_in_executor(None, input)
            except EOFError:
                LOGGER.info("EOF received; dissolving room")
                await self._queue.put(
                    PresenceEvent("exit", None, 0.0, time.monotonic())
                )
                self._stop.set()
                break
            except KeyboardInterrupt:
                LOGGER.info("Keyboard interrupt; dissolving room")
                await self._queue.put(
                    PresenceEvent("exit", None, 0.0, time.monotonic())
                )
                self._stop.set()
                break

            if text is None:
                continue

            cleaned = text.strip("\r")
            delay = random.uniform(*self._response_delay)
            await self._queue.put(
                PresenceEvent("input", cleaned, delay, time.monotonic())
            )
            self._next_idle = self._schedule_idle()

    async def _breath_worker(self) -> None:
        while not self._stop.is_set():
            timeout = max(0.0, self._next_idle - time.monotonic())
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=timeout)
                break
            except asyncio.TimeoutError:
                delay = random.uniform(*self._response_delay)
                await self._queue.put(
                    PresenceEvent("breath", None, delay, time.monotonic())
                )
                self._next_idle = self._schedule_idle()

    def _schedule_idle(self) -> float:
        span = random.uniform(*self._idle_breath)
        return time.monotonic() + span
