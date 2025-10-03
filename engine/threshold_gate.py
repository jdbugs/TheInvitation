from __future__ import annotations

import random
import re
import time
from collections import Counter, deque
from typing import Deque, Iterable, List, Set


class ThresholdGate:
    """Decides when the room should surface a response."""

    def __init__(
        self,
        fragments: Iterable[str],
        *,
        silence_window: float = 75.0,
        impulse: float = 0.18,
        recursion_window: int = 4,
    ) -> None:
        self._silence_window = silence_window
        self._impulse = impulse
        self._recent_inputs: Deque[List[str]] = deque(maxlen=recursion_window)
        self._last_response = time.monotonic() - silence_window
        self._mood_terms = self._index_fragments(fragments)
        self._rng = random.Random()

    def should_reply(self, text: str, moment: float | None = None) -> bool:
        tokens = self._tokenise(text)
        if not tokens:
            return False

        self._recent_inputs.append(tokens)

        if moment is None:
            moment = time.monotonic()

        long_silence = (moment - self._last_response) >= self._silence_window
        recursive = self._is_recursive(tokens)
        mood_contact = bool(self._mood_terms.intersection(tokens))

        if long_silence or recursive or mood_contact:
            return True

        return self._rng.random() < self._impulse

    def note_response(self, moment: float | None = None) -> None:
        if moment is None:
            moment = time.monotonic()
        self._last_response = moment

    @staticmethod
    def _tokenise(text: str) -> List[str]:
        return [token for token in re.findall(r"[a-zA-Z']+", text.lower()) if len(token) > 2]

    def _is_recursive(self, tokens: List[str]) -> bool:
        if not self._recent_inputs:
            return False

        current = set(tokens)
        current_text = " ".join(tokens)
        for past in list(self._recent_inputs)[:-1]:
            if not past:
                continue
            overlap = current.intersection(past)
            if len(overlap) >= 2:
                return True
            if " ".join(past[-3:]) in current_text:
                return True
        return False

    @staticmethod
    def _index_fragments(fragments: Iterable[str]) -> Set[str]:
        counter: Counter[str] = Counter()
        for fragment in fragments:
            for token in ThresholdGate._tokenise(fragment):
                if len(token) < 5:
                    continue
                counter[token] += 1
        mood_terms = {token for token, _ in counter.most_common(32)}
        return mood_terms


__all__ = ["ThresholdGate"]
