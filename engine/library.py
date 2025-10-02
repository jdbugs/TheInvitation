"""Seed harvesting utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
import logging
import random

from .configuration import LibraryConfig

LOGGER = logging.getLogger("invitation.library")


@dataclass(frozen=True)
class SeedFragment:
    text: str
    source: str


class SeedLibrary:
    """Loads text fragments from the ``data`` directory."""

    def __init__(self, seeds: Iterable[SeedFragment], config: LibraryConfig) -> None:
        self._seeds: List[SeedFragment] = list(seeds)
        self._config = config
        self._rng = random.Random()
        if not self._seeds:
            LOGGER.warning("seed library is empty; responses will fall back to defaults")

    @classmethod
    def from_path(cls, path: Path, config: LibraryConfig) -> "SeedLibrary":
        seeds: list[SeedFragment] = []
        for file in sorted(path.glob("**/*")):
            if not file.is_file():
                continue
            if file.suffix.lower() not in {".txt", ".md"}:
                continue
            seeds.extend(cls._harvest_file(file, config))
        LOGGER.info("library harvested %d fragments", len(seeds))
        return cls(seeds, config)

    def pick(self, count: int) -> list[SeedFragment]:
        if not self._seeds:
            return []
        limit = min(count, len(self._seeds), max(1, self._config.max_fragments))
        if limit == len(self._seeds):
            return list(self._seeds)
        return self._rng.sample(self._seeds, k=limit)

    @staticmethod
    def _harvest_file(file: Path, config: LibraryConfig) -> list[SeedFragment]:
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            LOGGER.warning("skipping non-text file %s", file)
            return []
        blocks = [segment.strip() for segment in text.split("\n\n")]
        results: list[SeedFragment] = []
        for block in blocks:
            cleaned = " ".join(part.strip() for part in block.splitlines()).strip()
            if not cleaned:
                continue
            if len(cleaned.split()) < config.min_words:
                continue
            clipped = _clip(cleaned, config.clip_chars)
            results.append(SeedFragment(text=clipped, source=file.name))
        return results


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    trimmed = text[: limit - 1].rstrip()
    last_space = trimmed.rfind(" ")
    if last_space > 0:
        trimmed = trimmed[:last_space]
    return f"{trimmed}…"


__all__ = ["SeedFragment", "SeedLibrary"]
