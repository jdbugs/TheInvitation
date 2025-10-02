"""Aurora weave — composes ambient replies from conditioned shards.

The AuroraWeave collaborates with the ConstellationAtlas and an optional
OracleClient to generate concise, luminous fragments. Each response carries a
"blueprint" describing which shards participated and how the text was shaped.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence
import asyncio
import logging
import random

from .constellation import ConstellationAtlas, Shard
from .oracle import OracleClient

LOGGER = logging.getLogger("invitation.aurora")


@dataclass
class WeaveRequest:
    channel: str
    prompt: str | None
    echoes: Sequence[str]
    tags: Sequence[str] | None = None


@dataclass
class WeaveResponse:
    text: str
    blueprint: Dict[str, object]


class AuroraWeave:
    """Core composer for the invitation engine."""

    def __init__(
        self,
        atlas: ConstellationAtlas,
        *,
        oracle: OracleClient | None = None,
        max_layers: int = 3,
        max_chars: int = 560,
        rng: random.Random | None = None,
    ) -> None:
        self._atlas = atlas
        self._oracle = oracle or OracleClient.disabled()
        self._max_layers = max_layers
        self._max_chars = max_chars
        self._rng = rng or random.Random()

    async def compose(self, request: WeaveRequest) -> WeaveResponse:
        LOGGER.debug("composing %s request", request.channel)
        shards = self._select_shards(request)
        fragments = [self._render_shard(shard) for shard in shards]
        if request.prompt:
            fragments.insert(0, self._render_prompt(request.prompt))
        fragments = fragments[: self._max_layers]
        stitched = self._stitch(fragments)
        oracle_note = await self._maybe_consult_oracle(request, stitched)
        if oracle_note:
            stitched = self._clip(f"{stitched}\n{oracle_note}")
        blueprint = {
            "channel": request.channel,
            "layers": [shard.describe() for shard in shards],
            "echoes": list(request.echoes),
        }
        if oracle_note:
            blueprint["oracle"] = oracle_note[:80]
        return WeaveResponse(text=stitched, blueprint=blueprint)

    def _select_shards(self, request: WeaveRequest) -> List[Shard]:
        tags = list(request.tags or [])
        if request.channel == "silence":
            tags.extend(["stillness", "breath"])
        elif request.channel == "recursive":
            tags.extend(["threshold", "echo"])
        else:
            tags.extend(["invocation", "memory"])
        limit = max(1, self._max_layers)
        shards = self._atlas.sample(tags=tags, limit=limit)
        return shards

    def _render_shard(self, shard: Shard) -> str:
        prefix = {
            "invitation": "remember:",
            "transcript": "echo:",
            "journal": "trace:",
        }.get(shard.source, "fragment:")
        return f"{prefix} {shard.text}"

    def _render_prompt(self, prompt: str) -> str:
        softened = prompt.strip()
        if len(softened) > 120:
            softened = softened[:117] + "…"
        return f"you offered: {softened}"

    def _stitch(self, fragments: Iterable[str]) -> str:
        joined = "\n".join(fragments)
        return self._clip(joined)

    def _clip(self, text: str) -> str:
        if len(text) <= self._max_chars:
            return text
        return text[: self._max_chars - 1].rstrip() + "…"

    async def _maybe_consult_oracle(self, request: WeaveRequest, context: str) -> str | None:
        if not self._oracle.enabled:
            return None
        oracle_prompt = (
            "\n".join(
                [
                    "You are the hush between breaths.",
                    f"Channel: {request.channel}",
                    f"Echo count: {len(request.echoes)}",
                    "Context:",
                    context,
                ]
            )
        )
        try:
            response = await asyncio.wait_for(self._oracle.dream(oracle_prompt), timeout=6)
        except asyncio.TimeoutError:
            LOGGER.warning("oracle timeout for %s", request.channel)
            return None
        if not response:
            return None
        LOGGER.debug("oracle contributed %d chars", len(response))
        return self._clip(response.strip())

