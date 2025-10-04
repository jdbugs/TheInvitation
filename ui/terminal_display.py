from __future__ import annotations

import asyncio
import random
import sys


class TerminalDisplay:
    """Renders output slowly to encourage lingering."""

    def __init__(
        self,
        *,
        char_delay: tuple[float, float] = (0.02, 0.07),
        line_pause: tuple[float, float] = (0.8, 1.6),
    ) -> None:
        self._char_delay = char_delay
        self._line_pause = line_pause

    async def render(self, text: str) -> None:
        if not text:
            return

        lines = text.splitlines()
        for index, line in enumerate(lines):
            if index and line:
                await asyncio.sleep(random.uniform(*self._line_pause))
            await self._render_line(line)

        if text.endswith("\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()

    async def breathe(self, glyph: str = "…") -> None:
        sys.stdout.write(f"{glyph}\n")
        sys.stdout.flush()
        await asyncio.sleep(random.uniform(*self._line_pause))

    async def _render_line(self, line: str) -> None:
        if not line:
            sys.stdout.write("\n")
            sys.stdout.flush()
            return

        for ch in line:
            sys.stdout.write(ch)
            sys.stdout.flush()
            await asyncio.sleep(random.uniform(*self._char_delay))
        sys.stdout.write("\n")
        sys.stdout.flush()
