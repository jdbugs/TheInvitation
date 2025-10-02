"""Minimal terminal rendering for The Invitation."""
from __future__ import annotations

import asyncio
import sys
import textwrap
import threading
from datetime import datetime
from typing import Optional

from engine.ambient_output import AmbientFragment


class TerminalDisplay:
    """Handles all terminal IO while keeping the surface minimal."""

    def __init__(self, stream=None) -> None:
        self.stream = stream or sys.stdout
        self._lock = threading.Lock()
        self._start_time = datetime.now()

    async def initialize(self) -> None:
        message = (
            "\n"
            "(there is no prompt)\n"
            "wait. type only if compelled.\n"
        )
        await self._write(message)

    async def shutdown(self) -> None:
        await self._write("\nclosing the field.\n")

    async def render_fragment(self, fragment: AmbientFragment) -> None:
        header = "\n"
        body = self._format_text(fragment.text)
        footer = "\n"
        await self._write(header + body + footer)

    async def emit_breath(self) -> None:
        breath = "\u00b7"
        await self._write(f"\r{breath}")
        await asyncio.sleep(0.35)
        await self._write("\r ")

    def capture_input(self) -> Optional[str]:
        try:
            return sys.stdin.readline()
        except Exception:
            return None

    # ------------------------------------------------------------------
    def _format_text(self, text: str) -> str:
        wrapped = textwrap.fill(text, width=68)
        return wrapped

    async def _write(self, text: str) -> None:
        await asyncio.to_thread(self._write_sync, text)

    def _write_sync(self, text: str) -> None:
        with self._lock:
            self.stream.write(text)
            self.stream.flush()
