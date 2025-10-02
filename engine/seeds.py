"""Seed loading and conditioning utilities for The Invitation."""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence


@dataclass(frozen=True)
class SeedFragment:
    """A conditioned slice of source material."""

    text: str
    source: str
    tags: frozenset[str]

    def signature(self) -> str:
        base = f"{self.source}:{hash(self.text) & 0xFFFFFFFF:08x}"
        return base


class SeedLibrary:
    """Loads and samples bounded fragments from the project data directory."""

    def __init__(
        self,
        data_dir: Path,
        *,
        max_words: int = 60,
        max_chars: int = 360,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.max_words = max_words
        self.max_chars = max_chars
        self._fragments: Dict[str, List[SeedFragment]] = {
            "invitation": [],
            "journal": [],
            "transcript": [],
        }
        self._tag_index: Dict[str, List[SeedFragment]] = {}
        self._load_all()

    # ------------------------------------------------------------------
    def sample(
        self,
        source: str,
        *,
        mood: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        count: int = 1,
    ) -> List[SeedFragment]:
        pool = list(self._fragments.get(source, ()))
        if not pool:
            return []

        selection = pool

        tag_pool: List[str] = []
        if tags:
            tag_pool.extend(tag for tag in tags if tag)

        if mood and source == "journal":
            tag_pool.append(mood)

        if tag_pool:
            tag_set = frozenset(tag_pool)
            filtered = [frag for frag in pool if frag.tags & tag_set]
            if filtered:
                selection = filtered
        else:
            selection = pool

        if count >= len(selection):
            random.shuffle(selection)
            return selection[:count]

        return random.sample(selection, count)

    # ------------------------------------------------------------------
    def clip(self, text: str, *, max_words: Optional[int] = None, max_chars: Optional[int] = None) -> str:
        words_limit = max_words if max_words is not None else self.max_words
        char_limit = max_chars if max_chars is not None else self.max_chars
        cleaned = text.strip()
        if not cleaned:
            return ""

        words = cleaned.split()
        if len(words) > words_limit:
            words = words[:words_limit]
        clipped = " ".join(words)
        if len(clipped) > char_limit:
            trimmed = clipped[:char_limit]
            parts = trimmed.rsplit(" ", 1)
            if len(parts) > 1 and parts[0]:
                clipped = parts[0]
            else:
                clipped = trimmed
        clipped = clipped.rstrip()
        if clipped and clipped[-1] not in ".!?…":
            candidate = f"{clipped} …"
            if len(candidate) <= char_limit:
                clipped = candidate
            else:
                base = clipped[: max(0, char_limit - 2)].rstrip()
                clipped = f"{base} …" if base else "…"
        return clipped

    # ------------------------------------------------------------------
    def sources(self) -> Dict[str, List[SeedFragment]]:
        return {key: list(value) for key, value in self._fragments.items()}

    # ------------------------------------------------------------------
    def _load_all(self) -> None:
        self._load_invitation()
        self._load_journals()
        self._load_transcripts()

    # ------------------------------------------------------------------
    def _load_invitation(self) -> None:
        path = self.data_dir / "The_Invitation.txt"
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8", errors="ignore")
        self._register_many("invitation", self._chunk_text(text))

    # ------------------------------------------------------------------
    def _load_journals(self) -> None:
        path = self.data_dir / "journals.json"
        if not path.exists():
            return
        raw = path.read_text(encoding="utf-8", errors="ignore")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = []
        for entry in data:
            text = entry.get("text") or ""
            tags = self._infer_tags(text)
            self._register_many("journal", self._chunk_text(text), tags=tags)

    # ------------------------------------------------------------------
    def _load_transcripts(self) -> None:
        path = self.data_dir / "transcripts.txt"
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8", errors="ignore")
        self._register_many("transcript", self._chunk_text(text))

    # ------------------------------------------------------------------
    def _register_many(
        self,
        source: str,
        chunks: Iterable[str],
        *,
        tags: Optional[Sequence[str]] = None,
    ) -> None:
        for chunk in chunks:
            cleaned = " ".join(chunk.split())
            if not cleaned:
                continue
            bounded = self.clip(cleaned)
            fragment = SeedFragment(text=bounded, source=source, tags=frozenset(tags or []))
            self._fragments[source].append(fragment)
            for tag in fragment.tags:
                self._tag_index.setdefault(tag, []).append(fragment)

    # ------------------------------------------------------------------
    def _chunk_text(self, text: str) -> Iterator[str]:
        for block in self._split_on_blank_lines(text):
            yield from self._bounded_segments(block)

    # ------------------------------------------------------------------
    def _split_on_blank_lines(self, text: str) -> Iterator[str]:
        pieces = [segment.strip() for segment in re.split(r"\n{2,}", text) if segment.strip()]
        for piece in pieces:
            yield piece

    # ------------------------------------------------------------------
    def _bounded_segments(self, text: str) -> Iterator[str]:
        stripped = text.strip()
        if not stripped:
            return

        if self._within_bounds(stripped):
            yield stripped
            return

        sentences = re.split(r"(?<=[.!?])\s+", stripped)
        buffer: List[str] = []
        word_count = 0
        char_count = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            words = sentence.split()
            tentative_words = word_count + len(words)
            tentative_chars = char_count + len(sentence) + (1 if buffer else 0)
            if buffer and (tentative_words > self.max_words or tentative_chars > self.max_chars):
                joined = " ".join(buffer).strip()
                if joined:
                    if self._within_bounds(joined):
                        yield joined
                    else:
                        yield from self._chunk_by_words(joined)
                buffer = [sentence]
                word_count = len(words)
                char_count = len(sentence)
            else:
                buffer.append(sentence)
                word_count = tentative_words
                char_count = tentative_chars

        if buffer:
            joined = " ".join(buffer).strip()
            if joined:
                if self._within_bounds(joined):
                    yield joined
                else:
                    yield from self._chunk_by_words(joined)

    # ------------------------------------------------------------------
    def _chunk_by_words(self, text: str) -> Iterator[str]:
        words = text.split()
        cursor = 0
        while cursor < len(words):
            slice_words = words[cursor : cursor + self.max_words]
            chunk = " ".join(slice_words)
            if len(chunk) > self.max_chars:
                while len(chunk) > self.max_chars and len(slice_words) > 1:
                    slice_words = slice_words[:-1]
                    chunk = " ".join(slice_words)
            if len(chunk) > self.max_chars:
                chunk = chunk[: self.max_chars]
            chunk = chunk.strip()
            if chunk:
                yield chunk
            cursor += max(1, len(slice_words))

    # ------------------------------------------------------------------
    def _within_bounds(self, text: str) -> bool:
        words = text.split()
        if len(words) > self.max_words:
            return False
        if len(text) > self.max_chars:
            return False
        return True

    # ------------------------------------------------------------------
    def _infer_tags(self, text: str) -> Sequence[str]:
        lower = text.lower()
        tags: List[str] = []
        if any(word in lower for word in ["tired", "sleep", "rest"]):
            tags.append("fatigue")
        if any(word in lower for word in ["love", "kind", "tender"]):
            tags.append("tenderness")
        if any(word in lower for word in ["fear", "anx", "panic", "scared"]):
            tags.append("anxiety")
        if any(word in lower for word in ["alone", "lonely", "isolate"]):
            tags.append("solitude")
        if any(word in lower for word in ["surrender", "let go", "release"]):
            tags.append("surrender")
        if not tags:
            tags.append("neutral")
        return tags
