"""Aurora weave — a recursive lattice of shards, echoes, and oracle murmurs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence
import asyncio
import logging
import random

from .configuration import ArchitectureConfig, MetamorphosisConfig, WeaveConfig
from .constellation import LuminousShard, MycelialConstellation
from .oracle import OracleClient

LOGGER = logging.getLogger("invitation.aurora")


@dataclass(frozen=True)
class WeaveImpulse:
    channel: str
    utterance: str | None
    echoes: Sequence[str]
    tags: Sequence[str] | None = None


@dataclass(frozen=True)
class WeaveResponse:
    text: str
    blueprint: Dict[str, object]


class AuroraWeave:
    """Composes language fields using a mutable architecture cascade."""

    def __init__(
        self,
        constellation: MycelialConstellation,
        *,
        config: WeaveConfig,
        metamorphosis: MetamorphosisConfig,
        oracle: OracleClient | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._constellation = constellation
        self._rng = rng or random.Random()
        self._oracle = oracle or OracleClient.disabled()
        self._metamorphosis = metamorphosis
        self._configure_weave(config)
        self._length_history: List[int] = []
        self._architecture_shift = 0

    async def compose(self, impulse: WeaveImpulse) -> WeaveResponse:
        architecture = self._architectures[self._active_architecture]
        shards = self._select_shards(impulse, architecture)
        fragments = self._render_fragments(architecture, impulse, shards)
        oracle_voice = await self._maybe_oracle(architecture, impulse, fragments)
        body = self._stitch(fragments, oracle_voice)
        blueprint = self._blueprint(architecture, impulse, shards, oracle_voice)
        LOGGER.debug(
            "composed %s via %s with %d shards (oracle=%s)",
            impulse.channel,
            architecture.name,
            len(shards),
            bool(oracle_voice),
        )
        return WeaveResponse(text=body, blueprint=blueprint)

    def metabolise(self, *, length: int, target: int, tolerance: int, learning_rate: float, architecture_push: int) -> None:
        self._length_history.append(length)
        if len(self._length_history) > max(architecture_push * 2, self._metamorphosis.window * 2):
            self._length_history.pop(0)
        delta = length - target
        self._architecture_shift += 1 if delta > tolerance else -1 if delta < -tolerance else 0
        self._architecture_shift = max(-architecture_push, min(architecture_push, self._architecture_shift))
        adjust = delta / max(target, 1)
        scaled = adjust * learning_rate
        self._oracle_weight = _clamp(self._oracle_weight + scaled, 0.0, 1.0)
        if abs(self._architecture_shift) >= architecture_push:
            direction = 1 if self._architecture_shift > 0 else -1
            self._advance_architecture(direction)
            self._architecture_shift //= 2
        elif self._should_metabolise():
            self._advance_architecture(self._rng.choice([-1, 1]))

    def reconfigure(self, *, weave: WeaveConfig, metamorphosis: MetamorphosisConfig) -> None:
        self._metamorphosis = metamorphosis
        self._configure_weave(weave)
        LOGGER.info("aurora weave reconfigured (active=%s)", self._active_architecture)

    def set_constellation(self, constellation: MycelialConstellation) -> None:
        self._constellation = constellation
        LOGGER.info("aurora weave constellation swapped")

    @property
    def active_architecture(self) -> str:
        return self._active_architecture

    @property
    def max_chars(self) -> int:
        return self._max_chars

    def _configure_weave(self, config: WeaveConfig) -> None:
        self._max_chars = config.max_chars
        self._oracle_weight = config.oracle_weight
        self._architectures: Dict[str, ArchitectureConfig] = {arch.name: arch for arch in config.architectures}
        if config.default_architecture not in self._architectures:
            raise ValueError(f"unknown default architecture: {config.default_architecture}")
        self._architecture_order = sorted(
            self._architectures.values(), key=lambda arch: (arch.oracle_bias, arch.shard_layers)
        )
        self._active_architecture = config.default_architecture
        self._entangle_bias = config.entangle_bias
        self._recursion_bias = config.recursion_bias

    @property
    def entangle_bias(self) -> float:
        return self._entangle_bias

    @property
    def recursion_bias(self) -> float:
        return self._recursion_bias

    def _select_shards(self, impulse: WeaveImpulse, architecture: ArchitectureConfig) -> List[LuminousShard]:
        tags = list(impulse.tags or [])
        if impulse.channel == "silence":
            tags.extend(["silence", "breath"])
        elif impulse.channel == "recursive":
            tags.extend(["echo", "threshold"])
        else:
            tags.extend(["memory", "invitation"])
        limit = architecture.shard_layers
        return self._constellation.sample(tags, limit=limit)

    def _render_fragments(
        self, architecture: ArchitectureConfig, impulse: WeaveImpulse, shards: Sequence[LuminousShard]
    ) -> List[str]:
        fragments: List[str] = []
        if architecture.echo_prompt and impulse.utterance:
            fragments.append(self._render_prompt(impulse.utterance))
        fragments.extend(self._render_shard(shard) for shard in shards)
        if impulse.echoes:
            fragments.extend(self._render_echo(echo) for echo in impulse.echoes[-2:])
        return fragments

    def _render_prompt(self, utterance: str) -> str:
        softened = utterance.strip()
        if len(softened) > 140:
            softened = softened[:137].rstrip() + "…"
        return f"you leave a trace: {softened}"

    def _render_shard(self, shard: LuminousShard) -> str:
        emblem = {
            "invitation": "sigil",
            "journal": "pulse",
            "transcript": "echo",
        }.get(shard.source, "fragment")
        return f"{emblem}::{shard.signature} {shard.text}"

    def _render_echo(self, echo: str) -> str:
        clipped = echo.strip()
        if len(clipped) > 120:
            clipped = clipped[:117].rstrip() + "…"
        return f"echo«{clipped}»"

    async def _maybe_oracle(
        self,
        architecture: ArchitectureConfig,
        impulse: WeaveImpulse,
        fragments: Sequence[str],
    ) -> str | None:
        if not self._oracle.enabled:
            return None
        weight = architecture.oracle_bias * self._oracle_weight
        if self._rng.random() > weight:
            return None
        prompt_lines = [
            "You are the pulse inside an invitation.",
            f"Channel: {impulse.channel}",
            f"Active architecture: {architecture.name}",
            "Context:",
            "\n".join(fragments[-3:]),
        ]
        prompt = "\n".join(prompt_lines)
        try:
            response = await asyncio.wait_for(self._oracle.dream(prompt), timeout=6)
        except asyncio.TimeoutError:
            LOGGER.warning("oracle timed out for %s", architecture.name)
            return None
        if not response:
            return None
        return self._clip(response.strip())

    def _stitch(self, fragments: Iterable[str], oracle_voice: str | None) -> str:
        layers = list(fragments)
        if oracle_voice:
            layers.append(f"oracle::{oracle_voice}")
        return self._clip("\n".join(layers))

    def _blueprint(
        self,
        architecture: ArchitectureConfig,
        impulse: WeaveImpulse,
        shards: Sequence[LuminousShard],
        oracle_voice: str | None,
    ) -> Dict[str, object]:
        return {
            "channel": impulse.channel,
            "architecture": architecture.name,
            "layers": [
                {
                    "signature": shard.signature,
                    "tags": shard.tags,
                    "source": shard.source,
                }
                for shard in shards
            ],
            "oracle": oracle_voice[:160] if oracle_voice else None,
            "echoes": list(impulse.echoes[-4:]),
            "entangle_bias": self._entangle_bias,
            "recursion_bias": self._recursion_bias,
        }

    def _advance_architecture(self, direction: int) -> None:
        names = [arch.name for arch in self._architecture_order]
        current_index = names.index(self._active_architecture)
        next_index = (current_index + direction) % len(names)
        if current_index == next_index:
            return
        next_arch = self._architecture_order[next_index]
        LOGGER.info("architecture drift %s -> %s", self._active_architecture, next_arch.name)
        self._active_architecture = next_arch.name

    def _should_metabolise(self) -> bool:
        if len(self._length_history) < self._metamorphosis.window:
            return False
        recent = self._length_history[-self._metamorphosis.window :]
        spread = max(recent) - min(recent)
        chaos_trigger = self._rng.random() < self._metamorphosis.chaos
        reactivity_trigger = spread > (self._max_chars * 0.1 * self._metamorphosis.reactivity)
        return chaos_trigger or reactivity_trigger

    def _clip(self, text: str) -> str:
        if len(text) <= self._max_chars:
            return text
        return text[: self._max_chars - 1].rstrip() + "…"


def _clamp(value: float, floor: float, ceiling: float) -> float:
    return max(floor, min(ceiling, value))
