from __future__ import annotations

import random
import re
from collections import deque
from typing import Deque, Iterable


DEFAULT_ECHOES = [
    "wait. breathe. speak only when moved.",
    "Stay with the quiet.",
    "You can rest here for a moment.",
]


class EchoChamber:
    """Stores prior utterances and returns mutated echoes."""

    def __init__(self, capacity: int = 32) -> None:
        self._memory: Deque[str] = deque(maxlen=capacity)

    def ingest(self, text: str) -> None:
        if not text:
            return
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned:
                self._memory.append(cleaned)

    def drift(self) -> str:
        if not self._memory:
            return random.choice(DEFAULT_ECHOES)

        primary = random.choice(tuple(self._memory))
        fragment = self._slice(primary)

        if len(self._memory) > 1 and random.random() < 0.45:
            overlay = self._slice(random.choice(tuple(self._memory)))
            fragment = f"{fragment} // {overlay}"

        if random.random() < 0.35:
            fragment = fragment.lower()
        if random.random() < 0.4:
            fragment = f"… {fragment}"

        return fragment

    @staticmethod
    def _slice(text: str) -> str:
        tokens = EchoChamber._tokenise(text)
        if len(tokens) <= 4:
            return " ".join(tokens)
        start = random.randint(0, max(0, len(tokens) - 4))
        span = random.randint(3, min(8, len(tokens) - start))
        snippet = " ".join(tokens[start : start + span])
        if random.random() < 0.3:
            snippet = snippet.rstrip(".,;:!?")
        if random.random() < 0.5:
            snippet += " …"
        return snippet

    @staticmethod
    def _tokenise(text: str) -> Iterable[str]:
        return [token for token in re.split(r"\s+", text) if token]
