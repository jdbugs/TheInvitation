"""Terminal surface for the invitation engine."""
from __future__ import annotations

import asyncio
import logging

from engine.aurora import WeaveResponse
from voice.tts_interface import AmbientChorus

LOGGER = logging.getLogger("invitation.display")


class TerminalPortal:
    def __init__(
        self,
        *,
        writer=None,
        show_blueprint: bool = True,
        chorus: AmbientChorus | None = None,
    ) -> None:
        self._writer = writer or print
        self._lock = asyncio.Lock()
        self._show_blueprint = show_blueprint
        self._chorus = chorus

    async def banner(self) -> None:
        await self._emit_lines(
            [
                "(there is no prompt)",
                "wait. breathe. speak only when moved.",
            ]
        )

    async def emit(self, response: WeaveResponse) -> None:
        blueprint = response.blueprint
        channel = blueprint.get("channel", "?")
        architecture = blueprint.get("architecture", "?")
        layers = blueprint.get("layers", [])
        oracle_note = "oracle" if blueprint.get("oracle") else "shards"
        lines = ["", response.text]
        if self._show_blueprint:
            summary = f"[{channel}:{architecture}] {len(response.text)} chars :: {len(layers)} layers :: {oracle_note}"
            lines.append(summary)
        await self._emit_lines(lines)
        await self._speak(response.text)

    async def close(self) -> None:
        return None

    def apply_surface(self, *, show_blueprint: bool, chorus: AmbientChorus | None) -> None:
        self._show_blueprint = show_blueprint
        self._chorus = chorus

    async def _emit_lines(self, lines: list[str]) -> None:
        async with self._lock:
            for line in lines:
                self._writer(line)

    async def _speak(self, text: str) -> None:
        if not self._chorus or not getattr(self._chorus, "enabled", False) or not text.strip():
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._chorus.speak, text)
