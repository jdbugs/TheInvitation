"""Presence loop orchestrating silence, input, and ambient output."""
from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional, Sequence, Set

from .ambient_output import AmbientFragment, AmbientOutputEngine, ComposeContext
from .echo_logic import EchoChamber
from voice.tts_interface import AmbientTTS
from ui.terminal_display import TerminalDisplay


@dataclass
class PresenceConfig:
    min_delay: float = 10.0
    max_delay: float = 90.0
    silence_range: Sequence[float] = (45.0, 120.0)
    poll_interval: float = 1.0
    response_probability: float = 0.5
    breath_interval: Sequence[float] = (10.0, 20.0)


class PresenceLoop:
    """Coordinates asynchronous presence according to threshold triggers."""

    def __init__(
        self,
        composer: AmbientOutputEngine,
        echo: EchoChamber,
        display: TerminalDisplay,
        tts: Optional[AmbientTTS],
        config: PresenceConfig,
    ) -> None:
        self.composer = composer
        self.echo = echo
        self.display = display
        self.tts = tts
        self.config = config

        self._input_queue: asyncio.Queue[str] = asyncio.Queue()
        self._pending_tasks: Set[asyncio.Task[None]] = set()
        self._running = False

        self._last_input = time.monotonic()
        self._last_output = time.monotonic()
        self._silence_target = self._next_silence_target()
        self._next_breath = self._next_breath_time()

        self._silence_pending = False
        self._silence_token = 0

    # ------------------------------------------------------------------
    async def run(self) -> None:
        if self._running:
            return
        self._running = True
        await self.display.initialize()
        listener = asyncio.create_task(self._input_listener())
        try:
            while self._running:
                await self._process_events()
                await asyncio.sleep(self.config.poll_interval)
        finally:
            listener.cancel()
            await asyncio.gather(listener, return_exceptions=True)
            pending = list(self._pending_tasks)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            await self.display.shutdown()

    # ------------------------------------------------------------------
    async def _process_events(self) -> None:
        now = time.monotonic()

        # Handle queued inputs.
        while not self._input_queue.empty():
            user_text = self._input_queue.get_nowait()
            if not user_text:
                continue
            self._last_input = now
            self._silence_pending = False
            self._silence_target = self._next_silence_target()
            self.echo.register(user_text, kind="user")
            mood = self.echo.infer_mood(user_text)
            recursive = self.echo.detect_recursive_phrasing(user_text)

            if recursive:
                await self._schedule_response(reason="recursive", user_input=user_text, mood=mood)
            elif random.random() <= self.config.response_probability:
                await self._schedule_response(reason="input", user_input=user_text, mood=mood)

        # Silence trigger
        if not self._silence_pending and (now - self._last_input) >= self._silence_target:
            self._silence_token += 1
            await self._schedule_response(
                reason="silence",
                user_input=None,
                mood=None,
                silence_token=self._silence_token,
            )
            self._silence_pending = True

        # Ambient breath tick
        if now >= self._next_breath:
            await self.display.emit_breath()
            self._next_breath = self._next_breath_time()

    # ------------------------------------------------------------------
    async def _schedule_response(
        self,
        *,
        reason: str,
        user_input: Optional[str],
        mood: Optional[str],
        silence_token: Optional[int] = None,
    ) -> None:
        delay = random.uniform(self.config.min_delay, self.config.max_delay)

        async def _deliver() -> None:
            try:
                await asyncio.sleep(delay)
                if reason == "silence":
                    if silence_token is not None and silence_token != self._silence_token:
                        return
                    if not self._silence_pending:
                        return
                context = ComposeContext(reason=reason, user_input=user_input, mood=mood)
                fragment = await self.composer.compose(context)
                if fragment.text.strip():
                    await self._emit(fragment)
                self._last_output = time.monotonic()
            finally:
                if reason == "silence" and (
                    silence_token is None or silence_token == self._silence_token
                ):
                    self._silence_pending = False
                    self._silence_target = self._next_silence_target()

        task = asyncio.create_task(_deliver())
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # ------------------------------------------------------------------
    async def _emit(self, fragment: AmbientFragment) -> None:
        self.echo.register(fragment.text, kind="system")
        await self.display.render_fragment(fragment)
        if self.tts and self.tts.enabled:
            await self.tts.speak(fragment.text)

    # ------------------------------------------------------------------
    async def _input_listener(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            line = await loop.run_in_executor(None, self.display.capture_input)
            if line is None:
                await asyncio.sleep(0.5)
                continue
            cleaned = line.strip()
            if cleaned:
                await self._input_queue.put(cleaned)

    # ------------------------------------------------------------------
    def _next_silence_target(self) -> float:
        low, high = self.config.silence_range
        return random.uniform(low, high)

    # ------------------------------------------------------------------
    def _next_breath_time(self) -> float:
        low, high = self.config.breath_interval
        return time.monotonic() + random.uniform(low, high)
