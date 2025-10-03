from __future__ import annotations

import random
import textwrap
from typing import Iterable, Optional

from invitation.ambient import AmbientWeaver, BREATH_LINES
from engine.echo_logic import EchoChamber


class AmbientOutput:
    """Weaves oracle replies, fragments, and echoes into atmospheric text."""

    def __init__(self, fragments: Iterable[str]) -> None:
        self._weaver = AmbientWeaver(fragments)
        self._echo = EchoChamber()

    def observe(self, text: str) -> None:
        self._echo.ingest(text)

    def oracle_reply(self, prompt: str, oracle_text: str) -> str:
        self.observe(prompt)
        self.observe(oracle_text)
        softened = self._soft_trim(oracle_text)
        sections = [
            "— invitation —",
            f"You said: {prompt.strip()}",
            "",
            softened,
            "",
            self._echo.drift(),
            "",
            random.choice(BREATH_LINES),
        ]
        return "\n".join(section for section in sections if section is not None).strip()

    def fallback(self, prompt: str) -> str:
        self.observe(prompt)
        composed = self._weaver.compose(prompt)
        self.observe(composed)
        echo = self._echo.drift()
        return f"{composed}\n\n{echo}"

    def ambient_breath(self) -> Optional[str]:
        fragment = self._weaver.glimpse()
        echo = self._echo.drift()
        if not fragment and not echo:
            return None
        lines = ["— invitation —"]
        if fragment:
            lines.append(textwrap.fill(fragment, width=76))
        if echo:
            if lines:
                lines.append("")
            lines.append(echo)
        lines.append("")
        lines.append(random.choice(BREATH_LINES))
        assembled = "\n".join(lines)
        self.observe(assembled)
        return assembled

    @staticmethod
    def _soft_trim(text: str, limit: int = 420) -> str:
        stripped = text.strip()
        if len(stripped) <= limit:
            return stripped
        snippet = stripped[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
        return f"{snippet} …"
