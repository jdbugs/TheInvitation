"""Constellation atlas for the ambient invitation engine.

This module curates textual shards drawn from the source material and
conditions them into short, luminous fragments that can be recombined by the
composer. The atlas is intentionally opinionated: each shard is tagged, clipped,
and normalized so downstream code can orchestrate rituals without worrying
about runaway verbosity.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence
import json
import random
import re


_SHARD_CLIP = 360
_MIN_WORDS = 6


def _normalize(text: str) -> str:
    """Collapse whitespace and strip stray punctuation."""
    collapsed = re.sub(r"\s+", " ", text.strip())
    # Preserve em dashes and ellipses but trim trailing commas/periods.
    collapsed = re.sub(r"[,;]+$", "", collapsed)
    return collapsed


@dataclass(frozen=True)
class Shard:
    """A conditioned fragment of source text."""

    text: str
    source: str
    tags: Sequence[str]

    def describe(self) -> str:
        tag_display = ",".join(self.tags)
        return f"<{self.source}:{tag_display}> {self.text[:80]}…" if len(self.text) > 80 else f"<{self.source}:{tag_display}> {self.text}"


class ConstellationAtlas:
    """Loads, clips, and serves ritual shards for the composer."""

    def __init__(
        self,
        shards: Iterable[Shard],
        *,
        clip: int = _SHARD_CLIP,
        rng: random.Random | None = None,
    ) -> None:
        self._clip = clip
        self._rng = rng or random.Random()
        self._shards: List[Shard] = []
        self._by_tag: dict[str, List[Shard]] = {}
        for shard in shards:
            conditioned = self._condition(shard)
            if conditioned is None:
                continue
            self._shards.append(conditioned)
            for tag in conditioned.tags:
                self._by_tag.setdefault(tag, []).append(conditioned)
        if not self._shards:
            raise ValueError("ConstellationAtlas requires at least one shard")

    @classmethod
    def from_data_dir(
        cls,
        data_dir: Path,
        *,
        clip: int = _SHARD_CLIP,
        rng: random.Random | None = None,
    ) -> "ConstellationAtlas":
        """Factory that hydrates the atlas from the repository data files."""
        invitation = cls._ingest_invitation(data_dir / "The_Invitation.txt")
        transcripts = cls._ingest_transcripts(data_dir / "transcripts.txt")
        journals = cls._ingest_journals(data_dir / "journals.json")
        shards = list(invitation) + list(transcripts) + list(journals)
        return cls(shards, clip=clip, rng=rng)

    @staticmethod
    def _ingest_invitation(path: Path) -> Iterable[Shard]:
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        for paragraph in text.split("\n\n"):
            normalized = _normalize(paragraph)
            if not normalized:
                continue
            yield Shard(normalized, "invitation", ("invocation", "stillness"))

    @staticmethod
    def _ingest_transcripts(path: Path) -> Iterable[Shard]:
        if not path.exists():
            return []
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        buffer: List[str] = []
        for line in lines:
            if line.startswith("User:") or line.startswith("System:"):
                speaker, remainder = line.split(":", 1)
                buffer.append(f"{speaker.strip()} {remainder.strip()}")
            else:
                buffer.append(line)
            if len(buffer) >= 2:
                joined = _normalize(" ".join(buffer))
                buffer.clear()
                yield Shard(joined, "transcript", ("echo", "threshold"))
        if buffer:
            yield Shard(_normalize(" ".join(buffer)), "transcript", ("echo", "threshold"))

    @staticmethod
    def _ingest_journals(path: Path) -> Iterable[Shard]:
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        for entry in raw:
            text = entry.get("text") or ""
            for paragraph in text.split("\n\n"):
                normalized = _normalize(paragraph)
                if not normalized:
                    continue
                yield Shard(normalized, "journal", ("memory", "breath"))

    def _condition(self, shard: Shard) -> Shard | None:
        normalized = _normalize(shard.text)
        if not normalized:
            return None
        if len(normalized.split()) < _MIN_WORDS:
            return None
        clipped = normalized if len(normalized) <= self._clip else normalized[: self._clip - 1].rstrip() + "…"
        return Shard(clipped, shard.source, tuple(sorted(set(shard.tags))))

    def sample(self, *, tags: Sequence[str] | None = None, limit: int = 2) -> List[Shard]:
        """Draw a handful of shards optionally biased by tags."""
        if limit <= 0:
            return []
        pool: List[Shard]
        if tags:
            tagged: List[Shard] = []
            for tag in tags:
                tagged.extend(self._by_tag.get(tag, []))
            pool = tagged or self._shards
        else:
            pool = self._shards
        picks = self._rng.sample(pool, k=min(limit, len(pool)))
        # Deduplicate while preserving order.
        seen = set()
        unique: List[Shard] = []
        for shard in picks:
            if shard.text in seen:
                continue
            seen.add(shard.text)
            unique.append(shard)
        return unique

    def describe(self, limit: int = 5) -> List[str]:
        """Return human-readable shard descriptions for debugging."""
        preview = self._rng.sample(self._shards, k=min(limit, len(self._shards)))
        return [shard.describe() for shard in preview]

