"""Asynchronous presence loop."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import asyncio
import contextlib
import logging
import random
import sys
from typing import Deque

from .composer import ResponseComposer
from .configuration import FeedbackConfig, TimingConfig
from ui.terminal_display import TerminalPortal

LOGGER = logging.getLogger("invitation.presence")


@dataclass
class LoopSettings:
    timing: TimingConfig
    feedback: FeedbackConfig


class PresenceLoop:
    def __init__(
        self,
        composer: ResponseComposer,
        portal: TerminalPortal,
        settings: LoopSettings,
    ) -> None:
        self._composer = composer
        self._portal = portal
        self._timing = settings.timing
        self._feedback = settings.feedback
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._silence_task: asyncio.Task | None = None
        self._silence_token = 0
        self._recent: Deque[int] = deque(maxlen=self._timing.echo_memory)
        self._rng = random.Random()
        self._running = False

    async def run(self) -> None:
        if self._running:
            return
        self._running = True
        await self._portal.banner()
        reader = asyncio.create_task(self._reader())
        input_future = asyncio.create_task(self._queue.get())
        self._schedule_silence()
        try:
            while True:
                wait_set = {input_future}
                if self._silence_task:
                    wait_set.add(self._silence_task)
                done, _ = await asyncio.wait(wait_set, return_when=asyncio.FIRST_COMPLETED)
                if input_future in done:
                    text = input_future.result().strip()
                    input_future = asyncio.create_task(self._queue.get())
                    if text:
                        await self._handle_input(text)
                if self._silence_task and self._silence_task in done:
                    self._silence_task = None
                    self._schedule_silence()
        except asyncio.CancelledError:
            raise
        finally:
            reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader

    def apply(self, *, timing: TimingConfig, feedback: FeedbackConfig) -> None:
        self._timing = timing
        self._feedback = feedback
        self._recent = deque(self._recent, maxlen=self._timing.echo_memory)
        LOGGER.info(
            "timing updated (delay %.1f-%.1fs, silence %.1f-%.1fs)",
            timing.min_delay,
            timing.max_delay,
            timing.min_silence,
            timing.max_silence,
        )

    async def _handle_input(self, text: str) -> None:
        LOGGER.info("heard %d chars", len(text))
        self._cancel_silence()
        response = await self._composer.craft(user_text=text, channel="input")
        await self._portal.emit(response)
        self._remember(len(response.text))
        self._schedule_silence()

    def _schedule_silence(self) -> None:
        self._cancel_silence()
        delay = self._silence_delay()
        self._silence_token += 1
        token = self._silence_token
        LOGGER.debug("scheduling silence response in %.1fs", delay)
        self._silence_task = asyncio.create_task(self._deliver_silence(delay, token))

    def _cancel_silence(self) -> None:
        if self._silence_task:
            self._silence_task.cancel()
            self._silence_task = None

    async def _deliver_silence(self, delay: float, token: int) -> None:
        try:
            await asyncio.sleep(delay)
            if token != self._silence_token:
                return
            response = await self._composer.craft(user_text=None, channel="silence")
            await self._portal.emit(response)
            self._remember(len(response.text))
        except asyncio.CancelledError:
            raise

    def _silence_delay(self) -> float:
        base = self._rng.uniform(self._timing.min_silence, self._timing.max_silence)
        if not self._recent:
            return base
        average = sum(self._recent) / len(self._recent)
        if average > self._feedback.target_chars + self._feedback.tolerance:
            return max(self._timing.min_silence, base * 0.7)
        if average < self._feedback.target_chars - self._feedback.tolerance:
            return min(self._timing.max_silence, base * 1.3)
        return base

    async def _reader(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if line == "":
                await asyncio.sleep(0.05)
                continue
            await self._queue.put(line.rstrip("\n"))

    def _remember(self, length: int) -> None:
        self._recent.append(length)
__all__ = ["LoopSettings", "PresenceLoop"]
