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


@dataclass
class FeedbackSettings:
    target_length: int = 240
    tolerance: int = 80
    adjust_rate: float = 0.15
    architecture_shift: int = 4
    max_layers_ceiling: int = 5
    min_layers_floor: int = 1
    delay_floor: float = 4.0
    delay_ceiling: float = 120.0
    silence_floor: float = 20.0
    silence_ceiling: float = 240.0


class ThresholdObserver:
    """Coordinates input, silence, and recursive breath."""

    def __init__(
        self,
        composer: AuroraWeave,
        display,
        *,
        settings: ObserverSettings | None = None,
        feedback: FeedbackSettings | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._composer = composer
        self._display = display
        self._settings = settings or ObserverSettings()
        self._feedback = feedback or FeedbackSettings()
        self._loop = loop or asyncio.get_event_loop()
        self._rng = rng or random.Random()
        self._pending: List[asyncio.Task] = []
        self._silence_token = 0
        self._silence_task: asyncio.Task | None = None
        self._echoes: Deque[str] = deque(maxlen=self._settings.echo_memory)
        self._running = False
        self._recent_lengths: Deque[int] = deque(maxlen=max(2, self._feedback.architecture_shift * 2))
        self._drift = 0

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
                self._register_response(response)

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

    def update_settings(self, settings: ObserverSettings) -> None:
        LOGGER.info(
            "observer reconfigured (delay %.2f-%.2fs, silence %.2f-%.2fs, echo_memory=%s)",
            settings.min_delay,
            settings.max_delay,
            settings.min_silence,
            settings.max_silence,
            settings.echo_memory,
        )
        self._settings = settings
        self._echoes = deque(list(self._echoes)[-settings.echo_memory :], maxlen=settings.echo_memory)

    def apply_feedback(self, feedback: FeedbackSettings) -> None:
        LOGGER.info(
            "feedback tuning updated (target=%s, tolerance=%s, shift=%s)",
            feedback.target_length,
            feedback.tolerance,
            feedback.architecture_shift,
        )
        self._feedback = feedback
        self._recent_lengths = deque(list(self._recent_lengths)[-max(2, feedback.architecture_shift * 2) :], maxlen=max(2, feedback.architecture_shift * 2))

    def apply_config(self, settings: ObserverSettings, feedback: FeedbackSettings) -> None:
        self.update_settings(settings)
        self.apply_feedback(feedback)

    def _register_response(self, response: WeaveResponse) -> None:
        if not response.text:
            return
        self._recent_lengths.append(len(response.text))
        if len(self._recent_lengths) < 2:
            return
        average = sum(self._recent_lengths) / len(self._recent_lengths)
        delta = average - self._feedback.target_length
        if abs(delta) <= self._feedback.tolerance:
            self._drift = int(self._drift * 0.5)
            return
        if delta > 0:
            self._adjust_layers(-1)
            self._rescale_delays(1.0 + self._feedback.adjust_rate)
            self._drift = min(self._drift + 1, self._feedback.architecture_shift + 1)
        else:
            self._adjust_layers(1)
            self._rescale_delays(max(0.3, 1.0 - self._feedback.adjust_rate))
            self._drift = max(self._drift - 1, -(self._feedback.architecture_shift + 1))
        self._shift_architecture_if_needed()

    def _adjust_layers(self, delta: int) -> None:
        current = self._composer.max_layers
        target = current + delta
        target = min(self._feedback.max_layers_ceiling, max(self._feedback.min_layers_floor, target))
        if target != current:
            LOGGER.debug("adjusting layers from %s to %s", current, target)
            self._composer.reconfigure(max_layers=target)

    def _rescale_delays(self, factor: float) -> None:
        def clamp(value: float, floor: float, ceiling: float) -> float:
            return max(floor, min(ceiling, value))

        min_delay = clamp(self._settings.min_delay * factor, self._feedback.delay_floor, self._feedback.delay_ceiling)
        max_delay = clamp(self._settings.max_delay * factor, min_delay, self._feedback.delay_ceiling)
        min_silence = clamp(self._settings.min_silence * factor, self._feedback.silence_floor, self._feedback.silence_ceiling)
        max_silence = clamp(self._settings.max_silence * factor, min_silence, self._feedback.silence_ceiling)

        new_settings = ObserverSettings(
            min_delay=min_delay,
            max_delay=max_delay,
            min_silence=min_silence,
            max_silence=max_silence,
            echo_memory=self._settings.echo_memory,
        )
        self.update_settings(new_settings)

    def _shift_architecture_if_needed(self) -> None:
        if self._drift >= self._feedback.architecture_shift:
            if self._composer.architecture != "oracle":
                LOGGER.info("feedback drift shifting architecture -> oracle")
                self._composer.reconfigure(architecture="oracle")
            self._drift = self._feedback.architecture_shift // 2
        elif self._drift <= -self._feedback.architecture_shift:
            if self._composer.architecture != "constellation":
                LOGGER.info("feedback drift shifting architecture -> constellation")
                self._composer.reconfigure(architecture="constellation")
            self._drift = -(self._feedback.architecture_shift // 2)

