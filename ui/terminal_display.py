"""Terminal surface for the Invitation engine."""
from __future__ import annotations

import asyncio
import logging

from engine.composer import Response
from voice.tts_interface import AmbientChorus

LOGGER = logging.getLogger("invitation.display")


class TerminalPortal:
    def __init__(
        self,
        *,
        prefix: str,
        show_debug: bool,
        chorus: AmbientChorus | None = None,
        writer=None,
    ) -> None:
        self._prefix = prefix
        self._show_debug = show_debug
        self._chorus = chorus
        self._writer = writer or print
        self._lock = asyncio.Lock()

    async def banner(self) -> None:
        await self._emit_lines(
            [
                "(there is no prompt)",
                "wait. breathe. speak only when moved.",
            ]
        )

    async def emit(self, response: Response) -> None:
        lines = ["", self._prefix, response.text]
        if self._show_debug:
            oracle_note = "oracle" if response.used_oracle else "library"
            lines.append(f"[{response.channel}] {len(response.text)} chars :: {oracle_note}")
            for fragment in response.fragments:
                lines.append(f"  • {fragment.source}: {fragment.text}")
        await self._emit_lines(lines)
        await self._speak(response.text)

    async def close(self) -> None:
        return None

    def apply_surface(self, *, prefix: str, show_debug: bool, chorus: AmbientChorus | None) -> None:
        self._prefix = prefix
        self._show_debug = show_debug
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
