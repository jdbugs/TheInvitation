"""Terminal surface for the invitation engine."""
from __future__ import annotations

from typing import Any
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
        payload = ["", response.text]
        blueprint = response.blueprint
        sigil = blueprint.get("channel", "unknown")
        architecture = blueprint.get("architecture", "constellation")
        payload.append(
            f"[{sigil}:{architecture}] :: {len(response.text)} chars :: {len(blueprint.get('layers', []))} layers"
        )
        await self._emit_lines(payload)

    async def close(self) -> None:
        # Nothing to tear down for now.
        return None

    async def _emit_lines(self, lines: list[str]) -> None:
        async with self._lock:
            for line in lines:
                self._writer(line)

