"""Witness observer — orchestrates timing, recursion, and feedback loops."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, Iterable, List, Sequence
import asyncio
import logging
import random
from collections import deque

from .aurora import AuroraWeave, WeaveImpulse, WeaveResponse

LOGGER = logging.getLogger("invitation.observer")


@dataclass
class PulseSettings:
    min_delay: float
    max_delay: float
    min_silence: float
    max_silence: float
    echo_memory: int


@dataclass
class FeedbackTuning:
    target_chars: int
    tolerance: int
    learning_rate: float
    architecture_push: int
    max_layers_ceiling: int
    min_layers_floor: int
    delay_floor: float
    delay_ceiling: float
    silence_floor: float
    silence_ceiling: float


class WitnessObserver:
    """Coordinates the breathing loop with recursive feedback."""

    def __init__(
        self,
        weave: AuroraWeave,
        display,
        *,
        settings: PulseSettings,
        tuning: FeedbackTuning,
        loop: asyncio.AbstractEventLoop | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._weave = weave
        self._display = display
        self._settings = settings
        self._tuning = tuning
        self._loop = loop or asyncio.get_event_loop()
        self._rng = rng or random.Random()
        self._silence_token = 0
        self._silence_task: asyncio.Task | None = None
        self._pending: List[asyncio.Task] = []
        self._running = False
        self._echoes: Deque[str] = deque(maxlen=settings.echo_memory)
        self._recent_lengths: Deque[int] = deque(maxlen=max(4, tuning.architecture_push * 2))
        self._palette = ["presence", "threshold", "mirror", "surrender", "witness"]

    async def run(self) -> None:
        self._running = True
        await self._display.banner()
        LOGGER.info("witness observer initiated (architecture=%s)", self._weave.active_architecture)
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
        LOGGER.info("participant offered %d chars", len(clean))
        self._cancel_silence()
        await self._plan(channel="input", payload=clean, tags=["participant"])
        self._schedule_silence()

    async def trigger_recursive(self) -> None:
        await self._plan(channel="recursive", payload="", tags=["echo"])

    async def aclose(self) -> None:
        if not self._running:
            return
        self._running = False
        self._cancel_silence()
        for task in list(self._pending):
            task.cancel()
        self._pending.clear()
        await self._display.close()

    async def _read_line(self) -> str | None:
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, input)
        except (EOFError, KeyboardInterrupt):
            return None

    async def _plan(self, *, channel: str, payload: str, tags: Sequence[str]) -> None:
        delay = self._rng.uniform(self._settings.min_delay, self._settings.max_delay)
        signature = self._silence_token if channel == "silence" else None
        flavour = self._mutate_tags(tags)
        LOGGER.debug("planning %s in %.2fs with tags=%s", channel, delay, flavour)

        async def deliver(expected_token: int | None) -> None:
            if expected_token is not None and expected_token != self._silence_token:
                LOGGER.debug("stale silence task skipped")
                return
            await asyncio.sleep(delay)
            impulse = WeaveImpulse(
                channel=channel,
                utterance=payload or None,
                echoes=list(self._echoes),
                tags=flavour,
            )
            response = await self._weave.compose(impulse)
            await self._display.emit(response)
            if response.text:
                self._echoes.append(response.text)
                self._register_response(response)
                self._maybe_schedule_recursive()

        task = self._loop.create_task(deliver(signature))
        self._pending.append(task)
        task.add_done_callback(lambda fut: self._pending.remove(fut) if fut in self._pending else None)

    def _mutate_tags(self, tags: Sequence[str]) -> List[str]:
        palette = list(tags)
        if self._rng.random() < self._weave.entangle_bias:
            palette.append(self._rng.choice(self._palette))
        return palette

    def _schedule_silence(self) -> None:
        self._silence_token += 1
        token = self._silence_token
        delay = self._rng.uniform(self._settings.min_silence, self._settings.max_silence)
        LOGGER.debug("scheduling silence %s in %.2fs", token, delay)

        async def deliver() -> None:
            await asyncio.sleep(delay)
            await self._plan(channel="silence", payload="", tags=["silence"])

        if self._silence_task:
            self._silence_task.cancel()
        self._silence_task = self._loop.create_task(deliver())

    def _cancel_silence(self) -> None:
        self._silence_token += 1
        if self._silence_task:
            self._silence_task.cancel()
            self._silence_task = None

    def apply_config(self, *, settings: PulseSettings, tuning: FeedbackTuning) -> None:
        LOGGER.info("observer reconfigured (delay %.1f-%.1fs, silence %.1f-%.1fs)", settings.min_delay, settings.max_delay, settings.min_silence, settings.max_silence)
        self._settings = settings
        self._tuning = tuning
        self._echoes = deque(list(self._echoes)[-settings.echo_memory :], maxlen=settings.echo_memory)
        self._recent_lengths = deque(list(self._recent_lengths)[-max(4, tuning.architecture_push * 2) :], maxlen=max(4, tuning.architecture_push * 2))

    def _register_response(self, response: WeaveResponse) -> None:
        length = len(response.text)
        self._recent_lengths.append(length)
        tuning = self._tuning
        self._weave.metabolise(
            length=length,
            target=tuning.target_chars,
            tolerance=tuning.tolerance,
            learning_rate=tuning.learning_rate,
            architecture_push=tuning.architecture_push,
        )
        if len(self._recent_lengths) < 2:
            return
        average = sum(self._recent_lengths) / len(self._recent_lengths)
        if average > tuning.target_chars + tuning.tolerance:
            self._rescale_delays(1.0 + tuning.learning_rate)
        elif average < tuning.target_chars - tuning.tolerance:
            self._rescale_delays(max(0.2, 1.0 - tuning.learning_rate))

    def _rescale_delays(self, factor: float) -> None:
        def clamp(value: float, floor: float, ceiling: float) -> float:
            return max(floor, min(ceiling, value))

        settings = self._settings
        tuning = self._tuning
        min_delay = clamp(settings.min_delay * factor, tuning.delay_floor, tuning.delay_ceiling)
        max_delay = clamp(settings.max_delay * factor, min_delay, tuning.delay_ceiling)
        min_silence = clamp(settings.min_silence * factor, tuning.silence_floor, tuning.silence_ceiling)
        max_silence = clamp(settings.max_silence * factor, min_silence, tuning.silence_ceiling)
        self._settings = PulseSettings(
            min_delay=min_delay,
            max_delay=max_delay,
            min_silence=min_silence,
            max_silence=max_silence,
            echo_memory=settings.echo_memory,
        )
        LOGGER.debug(
            "delays rescaled to %.1f-%.1fs (silence %.1f-%.1fs)",
            min_delay,
            max_delay,
            min_silence,
            max_silence,
        )

    def _maybe_schedule_recursive(self) -> None:
        if self._rng.random() < self._weave.recursion_bias:
            self._loop.create_task(self.trigger_recursive())


__all__ = ["WitnessObserver", "PulseSettings", "FeedbackTuning"]
