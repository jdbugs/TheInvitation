"""Ambient output composition for The Invitation."""
from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from .echo_logic import EchoChamber
from .local_llm import LLMResult, LocalLLM
from .seeds import SeedFragment, SeedLibrary
from .ritual import ResonanceField


@dataclass
class ComposeContext:
    """Hints provided to the ambient composer."""

    reason: str
    user_input: Optional[str] = None
    recursion_level: int = 0
    mood: Optional[str] = None
    timestamp: Optional[float] = None


@dataclass
class AmbientFragment:
    """Structured container for ambient output."""

    text: str
    source: str
    metadata: Dict[str, str]
    layers: Optional[Sequence[str]] = None
    signature: Optional[str] = None


class AmbientOutputEngine:
    """Weaves seed fragments, echoes, and optional LLM drift."""

    def __init__(
        self,
        data_dir,
        echo_chamber: EchoChamber,
        llm: Optional[LocalLLM] = None,
        *,
        library: Optional[SeedLibrary] = None,
    ) -> None:
        self.echo = echo_chamber
        self.llm = llm
        self.library = library or SeedLibrary(data_dir)
        self.field = ResonanceField(self.library, echo_chamber)
        self._log = logging.getLogger("invitation.composer")

        if self.llm is not None:
            self.llm.set_fallback(self._fallback_from_seeds)

    # ------------------------------------------------------------------
    async def compose(self, context: ComposeContext) -> AmbientFragment:
        """Compose a fragment according to the present context."""

        self._log.info("assembling fragments for %s", context.reason)
        layers: List[str] = []

        trace = self.field.imprint_trace(context.user_input)
        if trace:
            layers.append(trace)

        blueprint = self.field.blueprint(reason=context.reason, mood=context.mood)
        ritual_layers = self.field.harvest(blueprint, mood=context.mood)
        layers.extend(ritual_layers)

        prepared = self._prepare_layers(layers)
        text = self._render(prepared)

        metadata: Dict[str, str] = {"reason": context.reason}
        metadata["blueprint"] = self.field.describe(blueprint)
        metadata["layer_count"] = str(len(prepared))

        if self.llm is not None:
            llm_text = await self._query_model(context, prepared, text)
            if llm_text:
                metadata["llm"] = self.llm.model
                text = self._merge_with_llm(text, llm_text)

        if not text.strip():
            text = "…"

        metadata["mood"] = context.mood or "undetermined"
        source = metadata.get("llm", "seeds")
        signature = self.field.signature(prepared) if prepared else self.field.signature([text])
        metadata["signature"] = signature
        history_length = len(self.field.history())
        metadata["witness_depth"] = str(history_length)
        self._log.debug("fragment ready (source=%s, length=%d)", source, len(text))
        return AmbientFragment(
            text=text,
            source=source,
            metadata=metadata,
            layers=tuple(prepared),
            signature=signature,
        )

    # ------------------------------------------------------------------
    def _prepare_layers(self, layers: Sequence[str]) -> List[str]:
        unique: List[str] = []
        seen = set()
        for layer in layers:
            cleaned = layer.strip()
            if not cleaned:
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            unique.append(cleaned)
        trimmed = [self.library.clip(item, max_words=48, max_chars=240) for item in unique]
        return trimmed[:3]

    # ------------------------------------------------------------------
    def _render(self, layers: Sequence[str]) -> str:
        if not layers:
            return ""
        wrapped = [textwrap.fill(layer, width=68) for layer in layers]
        combined = "\n\n".join(wrapped)
        words = combined.split()
        if len(words) > 90 or len(combined) > 480:
            clipped = self.library.clip(" ".join(words), max_words=90, max_chars=480)
            return textwrap.fill(clipped, width=68)
        return combined

    # ------------------------------------------------------------------
    def _merge_with_llm(self, base_text: str, llm_text: str) -> str:
        llm_clean = llm_text.strip()
        if not llm_clean:
            return base_text
        if not base_text.strip():
            return llm_clean
        return f"{base_text}\n\n{llm_clean}"

    # ------------------------------------------------------------------
    async def _query_model(
        self,
        context: ComposeContext,
        prepared_layers: Sequence[str],
        base_text: str,
    ) -> str:
        if self.llm is None:
            return ""

        prompt_lines = [
            "You are the ambient presence called The Invitation.",
            "You only offer short fragments (max 55 words).",
            "Respond with 1-3 lines. Leave silence if unsure.",
        ]

        if context.reason == "silence":
            prompt_lines.append("The participant has been quiet for a long stretch.")
        elif context.reason == "recursive":
            prompt_lines.append("They are looping their language. Offer a gentle mirror.")
        else:
            prompt_lines.append("They left a trace. Reflect without solving it.")

        if prepared_layers:
            prompt_lines.append("Seed fragments available:")
            for layer in prepared_layers[:3]:
                prompt_lines.append(f"- {layer[:160]}")

        if base_text.strip():
            prompt_lines.append("Current assembly:")
            prompt_lines.append(base_text)

        prompt_lines.append("Return only the fragment. No commentary.")
        prompt = "\n".join(prompt_lines)

        try:
            result: LLMResult = await self.llm.generate(prompt, max_tokens=120)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._log.warning("ollama request failed: %s", exc)
            return ""

        if result.used_fallback:
            self._log.info("ollama unavailable; using fallback fragment")
        else:
            self._log.info("ollama response received (%d chars)", len(result.text))

        return self.library.clip(result.text, max_words=55, max_chars=320)

    # ------------------------------------------------------------------
    def _fallback_from_seeds(self, prompt: str) -> str:
        fragments: List[SeedFragment] = []
        fragments.extend(self.library.sample("invitation", count=1))
        fragments.extend(self.library.sample("journal", count=1))
        fragments.extend(self.library.sample("transcript", count=1))
        if not fragments:
            return "silence"
        stitched = " / ".join(fragment.text for fragment in fragments if fragment.text)
        distilled = self.echo.distill_fragment(stitched, drift=0.4)
        return self.library.clip(distilled or stitched, max_words=40, max_chars=220)
