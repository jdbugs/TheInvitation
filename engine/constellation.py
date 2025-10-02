"""Mycelial constellation — harvests and mutates luminous shards."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence
import hashlib
import logging
import random
import re

from .configuration import FieldConfig

LOGGER = logging.getLogger("invitation.constellation")


_SHARD_SPLIT = re.compile(r"\n\s*\n")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class LuminousShard:
    """A conditioned language shard with provenance and signature."""

    text: str
    tags: tuple[str, ...]
    source: str
    signature: str


class MycelialConstellation:
    """Maintains a field of shards and provides adaptive sampling."""

    def __init__(
        self,
        shards: Sequence[LuminousShard],
        *,
        clip: int,
        min_slices: int,
        max_slices: int,
        base_tags: Sequence[str],
        mutation_rate: float,
        rng: random.Random | None = None,
    ) -> None:
        if not shards:
            raise ValueError("constellation requires at least one shard")
        self._shards = list(shards)
        self._clip = clip
        self._min_slices = min_slices
        self._max_slices = max(max_slices, min_slices)
        self._base_tags = tuple(base_tags)
        self._mutation_rate = mutation_rate
        self._rng = rng or random.Random()
        self._tag_index = self._build_index(shards)

    @classmethod
    def from_data_dir(
        cls,
        path: Path,
        config: FieldConfig,
        *,
        rng: random.Random | None = None,
    ) -> "MycelialConstellation":
        shards: List[LuminousShard] = []
        for file_path in sorted(path.glob("*.txt")):
            text = file_path.read_text(encoding="utf-8")
            for fragment in _normalise_and_clip(text, config.clip):
                tags = tuple(sorted(_derive_tags(file_path.name, fragment, config.base_tags)))
                signature = hashlib.sha256(f"{file_path.name}|{fragment}".encode("utf-8")).hexdigest()[:16]
                shards.append(
                    LuminousShard(
                        text=fragment,
                        tags=tags,
                        source=file_path.stem,
                        signature=signature,
                    )
                )
        if not shards:
            raise ValueError(f"no shards discovered under {path}")
        LOGGER.info("constellation loaded %s shards from %s", len(shards), path)
        return cls(
            shards,
            clip=config.clip,
            min_slices=config.min_slices,
            max_slices=config.max_slices,
            base_tags=config.base_tags,
            mutation_rate=config.mutation_rate,
            rng=rng,
        )

    def sample(self, tags: Sequence[str] | None, *, limit: int | None = None) -> List[LuminousShard]:
        limit = max(self._min_slices, min(self._max_slices, limit or self._max_slices))
        palette = list(tags or self._base_tags)
        if not palette:
            palette = list(self._base_tags)
        selection: List[LuminousShard] = []
        attempts = 0
        while len(selection) < limit and attempts < limit * 6:
            attempts += 1
            tag = self._rng.choice(palette)
            shard = self._pick_by_tag(tag)
            if shard not in selection:
                selection.append(self._mutate(shard))
        if len(selection) < limit:
            LOGGER.debug("sampling shortfall: %s < %s", len(selection), limit)
            remaining = [shard for shard in self._shards if shard not in selection]
            self._rng.shuffle(remaining)
            selection.extend(remaining[: max(0, limit - len(selection))])
        return selection[:limit]

    def describe(self) -> Mapping[str, int]:
        counts: dict[str, int] = {}
        for shard in self._shards:
            for tag in shard.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return counts

    def _pick_by_tag(self, tag: str) -> LuminousShard:
        bucket = self._tag_index.get(tag)
        if bucket:
            return self._rng.choice(bucket)
        return self._rng.choice(self._shards)

    def _mutate(self, shard: LuminousShard) -> LuminousShard:
        if self._rng.random() >= self._mutation_rate:
            return shard
        mutated_tags = list(shard.tags)
        if mutated_tags and self._base_tags:
            swap_index = self._rng.randrange(len(mutated_tags))
            mutated_tags[swap_index] = self._rng.choice(self._base_tags)
        whispered = shard.text
        if len(whispered) > self._clip:
            whispered = whispered[: self._clip - 1].rstrip() + "…"
        return LuminousShard(
            text=whispered,
            tags=tuple(sorted(mutated_tags)) or shard.tags,
            source=shard.source,
            signature=shard.signature,
        )

    def _build_index(self, shards: Sequence[LuminousShard]) -> Mapping[str, List[LuminousShard]]:
        index: dict[str, List[LuminousShard]] = {}
        for shard in shards:
            for tag in shard.tags:
                index.setdefault(tag, []).append(shard)
        return index


def _normalise_and_clip(text: str, clip: int) -> Iterable[str]:
    for chunk in _SHARD_SPLIT.split(text.strip()):
        cleaned = _WHITESPACE.sub(" ", chunk).strip()
        if not cleaned:
            continue
        if len(cleaned) > clip:
            cleaned = cleaned[: clip - 1].rstrip() + "…"
        yield cleaned


def _derive_tags(name: str, fragment: str, base_tags: Sequence[str]) -> Iterable[str]:
    tags = set(base_tags)
    if "journal" in name:
        tags.add("journal")
    if "invitation" in name:
        tags.add("invitation")
    if "transcript" in name:
        tags.add("transcript")
    lowered = fragment.lower()
    if "breath" in lowered:
        tags.add("breath")
    if "silence" in lowered:
        tags.add("silence")
    if "love" in lowered:
        tags.add("love")
    if "remember" in lowered:
        tags.add("memory")
    if "threshold" in lowered:
        tags.add("threshold")
    if "surrender" in lowered:
        tags.add("surrender")
    return tags
