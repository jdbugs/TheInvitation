from __future__ import annotations

import logging
import random
import textwrap
from typing import Iterable, List, Optional

LOGGER = logging.getLogger(__name__)


BREATH_LINES = [
    "wait. breathe. speak only when moved.",
    "Let the breath linger.",
    "Stay with the quiet.",
    "You can rest here for a moment.",
]


class AmbientWeaver:
    def __init__(self, fragments: Iterable[str]) -> None:
        self._fragments = list(fragments)
        self._cursor = 0
        if not self._fragments:
            LOGGER.warning("AmbientWeaver initialised without fragments; using breath lines only")

    def compose(self, user_line: str) -> str:
        parts: List[str] = []
        parts.append("— invitation —")
        if user_line.strip():
            parts.append(f"You said: {user_line.strip()}")
        parts.extend(self._sample_fragments(2))
        parts.append(random.choice(BREATH_LINES))
        return "\n\n".join(parts)

    def _sample_fragments(self, count: int) -> List[str]:
        if not self._fragments:
            return []
        selections: List[str] = []
        for _ in range(count):
            selections.append(self._next_fragment())
        return [textwrap.fill(entry, width=78) for entry in selections]

    def _next_fragment(self) -> str:
        if not self._fragments:
            return random.choice(BREATH_LINES)
        value = self._fragments[self._cursor]
        self._cursor = (self._cursor + 1) % len(self._fragments)
        return value

    def glimpse(self) -> Optional[str]:
        if not self._fragments:
            return None
        return self._next_fragment()
