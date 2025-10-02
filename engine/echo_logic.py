"""Logic for storing and mutating fragments within the echo chamber."""
from __future__ import annotations

import random
import re
from collections import Counter, deque
from dataclasses import dataclass
from typing import Deque, Iterable, List, Optional


@dataclass
class EchoRecord:
    text: str
    kind: str


class EchoChamber:
    """Maintains a reservoir of fragments and provides drift/mutation utilities."""

    def __init__(self, max_items: int = 64) -> None:
        self.max_items = max_items
        self.records: Deque[EchoRecord] = deque(maxlen=max_items)
        self._recent_inputs: Deque[str] = deque(maxlen=12)

    # ------------------------------------------------------------------
    def register(self, text: str, kind: str = "system") -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        self.records.append(EchoRecord(cleaned, kind))
        if kind == "user":
            self._recent_inputs.append(cleaned)

    # ------------------------------------------------------------------
    def mutate_text(self, text: str, intensity: float = 0.25) -> str:
        words = text.split()
        if not words:
            return text
        keep_count = max(1, int(len(words) * (1 - intensity * 0.8)))
        sampled = random.sample(words, k=min(len(words), keep_count))
        random.shuffle(sampled)
        fragment = " ".join(sampled)
        if random.random() < 0.3:
            fragment = fragment.lower()
        if random.random() < 0.4:
            fragment += " …"
        return fragment

    # ------------------------------------------------------------------
    def distill_fragment(self, text: str, drift: float = 0.2) -> str:
        tokens = re.findall(r"\w+|[.,;:?]", text)
        if not tokens:
            return text
        keep = []
        for token in tokens:
            if random.random() > drift:
                keep.append(token)
        if not keep:
            keep = tokens[: max(1, len(tokens) // 3)]
        merged = self._reassemble(keep)
        if random.random() < 0.35:
            merged = merged.strip().lower()
        return merged

    # ------------------------------------------------------------------
    def detect_recursive_phrasing(self, text: str) -> bool:
        normalized = self._normalize(text)
        recent = [self._normalize(entry) for entry in self._recent_inputs]
        if not normalized:
            return False
        if recent.count(normalized) >= 2:
            return True
        parts = normalized.split()
        counter = Counter(parts)
        return any(count >= 3 for count in counter.values())

    # ------------------------------------------------------------------
    def infer_mood(self, text: str) -> Optional[str]:
        lower = text.lower()
        if any(keyword in lower for keyword in ["tired", "sleep", "exhausted"]):
            return "fatigue"
        if any(keyword in lower for keyword in ["alone", "lonely", "solitude"]):
            return "solitude"
        if any(keyword in lower for keyword in ["panic", "scared", "afraid", "anxious"]):
            return "anxiety"
        if any(keyword in lower for keyword in ["love", "warm", "tender"]):
            return "tenderness"
        if any(keyword in lower for keyword in ["surrender", "let go", "release"]):
            return "surrender"
        return None

    # ------------------------------------------------------------------
    def retrieve_recent(self, limit: int = 3) -> List[str]:
        return [record.text for record in list(self.records)[-limit:]]

    # ------------------------------------------------------------------
    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    # ------------------------------------------------------------------
    def _reassemble(self, tokens: Iterable[str]) -> str:
        output: List[str] = []
        for token in tokens:
            if token in ",.;:?" and output:
                output[-1] += token
            else:
                output.append(token)
        return " ".join(output)
