"""Terminal surface for the invitation engine."""
from __future__ import annotations

import asyncio
import logging

from engine.aurora import WeaveResponse

LOGGER = logging.getLogger("invitation.display")


class TerminalPortal:
    def __init__(self, *, writer=None) -> None:
        self._writer = writer or print
        self._lock = asyncio.Lock()

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
        summary = f"[{channel}:{architecture}] {len(response.text)} chars :: {len(layers)} layers :: {oracle_note}"
        await self._emit_lines(["", response.text, summary])

    async def close(self) -> None:
        return None

    async def _emit_lines(self, lines: list[str]) -> None:
        async with self._lock:
            for line in lines:
                self._writer(line)
