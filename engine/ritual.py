"""Resonance rituals for weaving fragments beyond the literal."""
from __future__ import annotations

import hashlib
import logging
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

from .echo_logic import EchoChamber
from .seeds import SeedFragment, SeedLibrary


@dataclass(frozen=True)
class PulsePlan:
    """Blueprint for a single wave of gathered material."""

    name: str
    sources: Sequence[str]
    count: int
    tags: Sequence[str] = ()
    scatter: float = 0.0
    allow_empty: bool = False


class ResonanceField:
    """Harvests echoes, seeds, and traces into ritualised layers."""

    def __init__(self, library: SeedLibrary, echo: EchoChamber) -> None:
        self.library = library
        self.echo = echo
        self._log = logging.getLogger("invitation.field")
        self._witness_log: List[str] = []
        self._opened_at = time.monotonic()
        self._random = random.Random()

    # ------------------------------------------------------------------
    def imprint_trace(self, user_input: Optional[str]) -> Optional[str]:
        """Fold a user's words into the witness log."""

        if not user_input:
            return None
        mutated = self.echo.mutate_text(user_input, intensity=0.45)
        distilled = self.echo.distill_fragment(mutated, drift=0.35) if mutated else ""
        clipped = self.library.clip(distilled or user_input, max_words=32, max_chars=210)
        if clipped:
            self._witness_log.append(clipped)
            self._witness_log = self._witness_log[-16:]
        return clipped

    # ------------------------------------------------------------------
    def blueprint(self, *, reason: str, mood: Optional[str]) -> List[PulsePlan]:
        """Return a ritual plan describing which channels to harvest."""

        plans: List[PulsePlan] = [
            PulsePlan(name="recent-echo", sources=("echo",), count=1, allow_empty=True, scatter=0.15),
        ]
        if reason == "silence":
            plans.extend(
                [
                    PulsePlan(name="invocation", sources=("invitation",), count=2),
                    PulsePlan(
                        name="memory",
                        sources=("journal",),
                        count=1,
                        tags=self._mood_tags(mood, default=("surrender", "solitude")),
                    ),
                ]
            )
        elif reason == "recursive":
            plans.extend(
                [
                    PulsePlan(name="loop", sources=("transcript",), count=1, tags=("loop",)),
                    PulsePlan(
                        name="soften",
                        sources=("journal",),
                        count=1,
                        tags=self._mood_tags(mood, default=("tenderness", "surrender")),
                    ),
                ]
            )
        else:
            plans.extend(
                [
                    PulsePlan(
                        name="attune",
                        sources=("journal",),
                        count=2,
                        tags=self._mood_tags(mood, default=("neutral", "tenderness")),
                    ),
                    PulsePlan(name="invocation", sources=("invitation",), count=1),
                ]
            )
        return plans

    # ------------------------------------------------------------------
    def harvest(self, plans: Sequence[PulsePlan], *, mood: Optional[str]) -> List[str]:
        """Collect textual layers according to the blueprint."""

        layers: List[str] = []
        for plan in plans:
            collected = self._collect_plan(plan, mood)
            if not collected and not plan.allow_empty:
                continue
            layers.extend(collected)
        return layers

    # ------------------------------------------------------------------
    def signature(self, layers: Sequence[str]) -> str:
        """Forge a small sigil for the present weave."""

        digest = hashlib.sha1("||".join(layers).encode("utf-8")).hexdigest()
        return f"sigil-{digest[:12]}"

    # ------------------------------------------------------------------
    def describe(self, plans: Sequence[PulsePlan]) -> str:
        """Return a lightweight human description of the blueprint."""

        parts = [f"{plan.name}:{'+'.join(plan.sources)}x{plan.count}" for plan in plans]
        return ",".join(parts)

    # ------------------------------------------------------------------
    def _collect_plan(self, plan: PulsePlan, mood: Optional[str]) -> List[str]:
        if all(source == "echo" for source in plan.sources):
            return self._echo_layers(plan)

        gathered: List[SeedFragment] = []
        effective_tags = self._resolve_tags(plan.tags, mood)
        quota = max(1, plan.count // max(1, len(plan.sources)))

        for source in plan.sources:
            picks = self.library.sample(source, tags=effective_tags, count=quota)
            gathered.extend(picks)

        if len(gathered) > plan.count:
            self._random.shuffle(gathered)
            gathered = gathered[: plan.count]

        clipped = [self.library.clip(fragment.text, max_words=48, max_chars=230) for fragment in gathered]
        return [layer for layer in clipped if layer]

    # ------------------------------------------------------------------
    def _echo_layers(self, plan: PulsePlan) -> List[str]:
        recent = list(self.echo.retrieve_recent(limit=plan.count * 3))
        if not recent:
            return []
        self._random.shuffle(recent)
        layers: List[str] = []
        for entry in recent[: plan.count]:
            drift = 0.25 + plan.scatter
            mutated = self.echo.distill_fragment(entry, drift=drift)
            clipped = self.library.clip(mutated or entry, max_words=36, max_chars=180)
            if clipped:
                layers.append(clipped)
        return layers

    # ------------------------------------------------------------------
    def _mood_tags(self, mood: Optional[str], default: Sequence[str]) -> Sequence[str]:
        if mood:
            return (mood,)
        return default

    # ------------------------------------------------------------------
    def _resolve_tags(self, tags: Sequence[str], mood: Optional[str]) -> Sequence[str]:
        resolved: List[str] = []
        for tag in tags:
            if tag == "@mood":
                if mood:
                    resolved.append(mood)
            else:
                resolved.append(tag)
        return tuple(resolved) if resolved else self._mood_tags(mood, default=("neutral",))

    # ------------------------------------------------------------------
    def history(self) -> Sequence[str]:
        return tuple(self._witness_log)
