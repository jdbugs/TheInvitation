"""Ambient text composition utilities."""
from __future__ import annotations

import logging
import random
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .echo_logic import EchoChamber
from .local_llm import LLMResult, LocalLLM


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


class AmbientOutputEngine:
    """Builds recursive, slow text fragments from seed materials."""

    def __init__(
        self,
        data_dir: Path,
        echo_chamber: EchoChamber,
        llm: Optional[LocalLLM] = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.echo = echo_chamber
        self.llm = llm

        self._invitation_fragments: List[Dict[str, str]] = []
        self._journal_fragments: List[Dict[str, str]] = []
        self._transcript_fragments: List[Dict[str, str]] = []

        self._log = logging.getLogger("invitation.composer")

        self._load_seed_material()
        if self.llm is not None:
            self.llm.set_fallback(self._fallback_from_seeds)

    # ------------------------------------------------------------------
    async def compose(self, context: ComposeContext) -> AmbientFragment:
        """Compose a new ambient fragment according to the provided context."""

        fragments: List[str] = []
        metadata: Dict[str, str] = {"reason": context.reason}
        self._log.info("assembling fragments for %s", context.reason)

        if context.user_input:
            mutated = self.echo.mutate_text(context.user_input, intensity=0.35)
            if mutated:
                fragments.append(mutated)

        if random.random() < 0.5:
            recent = self.echo.retrieve_recent(limit=1)
            for frag in recent:
                drifted = self.echo.distill_fragment(frag, drift=0.45)
                if drifted:
                    fragments.append(drifted)

        if context.reason == "silence":
            fragments.extend(self._draw_seed_set(weight="invitation", count=2))
        elif context.reason == "recursive":
            fragments.extend(self._draw_seed_set(weight="transcript", count=1))
            fragments.extend(self._draw_seed_set(weight="journal", count=1, mood=context.mood))
        else:
            fragments.extend(self._draw_seed_set(weight="journal", count=2, mood=context.mood))

        fragments = [self.echo.distill_fragment(f, drift=0.25) for f in fragments if f]
        fragments = [f for f in fragments if f]

        text = self._stitch_fragments(fragments)

        if self.llm is not None:
            llm_text = await self._query_model(context, fragments, text)
            if llm_text:
                metadata["llm"] = self.llm.model
                text = self._merge_with_llm(text, llm_text)
                self._log.debug("merged LLM response into fragment")
            else:
                self._log.debug("LLM returned no text; using seed composition")

        source = metadata.get("llm", "seeds")
        metadata["mood"] = context.mood or "undetermined"
        self._log.debug("fragment ready (source=%s, length=%d)", source, len(text))
        return AmbientFragment(text=text, source=source, metadata=metadata)

    # ------------------------------------------------------------------
    def _load_seed_material(self) -> None:
        invitation_path = self.data_dir / "The_Invitation.txt"
        if invitation_path.exists():
            invitation_text = invitation_path.read_text(encoding="utf-8", errors="ignore")
            self._invitation_fragments = self._split_into_fragments(
                invitation_text,
                source="invitation",
            )

        journal_path = self.data_dir / "journals.json"
        if journal_path.exists():
            import json

            journal_data = json.loads(journal_path.read_text(encoding="utf-8"))
            for entry in journal_data:
                text = entry.get("text", "")
                tags = self._infer_tags(text)
                fragments = self._split_into_fragments(text, source="journal", extra_tags=tags)
                self._journal_fragments.extend(fragments)

        transcript_path = self.data_dir / "transcripts.txt"
        if transcript_path.exists():
            transcript_text = transcript_path.read_text(encoding="utf-8", errors="ignore")
            fragments = self._split_into_fragments(transcript_text, source="transcript")
            self._transcript_fragments.extend(fragments)

    # ------------------------------------------------------------------
    def _split_into_fragments(
        self,
        text: str,
        source: str,
        extra_tags: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, str]]:
        chunks = [segment.strip() for segment in re.split(r"\n{2,}", text) if segment.strip()]
        fragments: List[Dict[str, str]] = []
        for chunk in chunks:
            compact = " ".join(line.strip() for line in chunk.splitlines())
            fragments.append(
                {
                    "text": compact,
                    "source": source,
                    "tags": list(extra_tags or []),
                }
            )
        return fragments

    # ------------------------------------------------------------------
    def _infer_tags(self, text: str) -> Sequence[str]:
        lower = text.lower()
        tags: List[str] = []
        if any(word in lower for word in ["tired", "sleep", "rest"]):
            tags.append("fatigue")
        if any(word in lower for word in ["love", "kind", "tender"]):
            tags.append("tenderness")
        if any(word in lower for word in ["fear", "anx", "panic"]):
            tags.append("anxiety")
        if any(word in lower for word in ["alone", "lonely", "isolate"]):
            tags.append("solitude")
        if any(word in lower for word in ["surrender", "let go", "release"]):
            tags.append("surrender")
        if not tags:
            tags.append("neutral")
        return tags

    # ------------------------------------------------------------------
    def _draw_seed_set(self, weight: str, count: int, mood: Optional[str] = None) -> List[str]:
        pool: List[Dict[str, str]]
        if weight == "invitation":
            pool = self._invitation_fragments
        elif weight == "journal":
            pool = self._journal_fragments
        else:
            pool = self._transcript_fragments

        if not pool:
            return []

        filtered = pool
        if mood and weight == "journal":
            filtered = [frag for frag in pool if mood in frag.get("tags", [])]
            if not filtered:
                filtered = pool

        return [random.choice(filtered)["text"] for _ in range(count)]

    # ------------------------------------------------------------------
    def _stitch_fragments(self, fragments: Sequence[str]) -> str:
        if not fragments:
            return ""
        combined = []
        for frag in fragments:
            wrapped = textwrap.fill(frag, width=72)
            combined.append(wrapped)
        return "\n\n".join(combined)

    # ------------------------------------------------------------------
    def _merge_with_llm(self, base_text: str, llm_text: str) -> str:
        if not llm_text:
            return base_text
        llm_text = llm_text.strip()
        if not base_text:
            return llm_text
        return f"{base_text}\n\n{llm_text}"

    # ------------------------------------------------------------------
    async def _query_model(self, context: ComposeContext, seeds: Sequence[str], base_text: str) -> str:
        if self.llm is None:
            return ""

        prompt_parts = [
            "You are an ambient recursive presence.",
            "You speak rarely, in fragments, without answers.",
            "You respond with 1-3 lines, under 55 words total.",
            "Avoid instructions. Offer space, silence, or breath.",
        ]
        if context.reason == "silence":
            prompt_parts.append("The user has been silent for a long stretch. Offer a gentle echo of presence.")
        elif context.reason == "recursive":
            prompt_parts.append("The user is looping through similar phrases. Allow a mirrored drift with variation.")
        else:
            prompt_parts.append("The user left a trace. Reflect without solving.")

        if seeds:
            prompt_parts.append("Fragments available:")
            for seed in seeds:
                prompt_parts.append(f"- {seed[:200]}")

        if base_text:
            prompt_parts.append("Current assembly:")
            prompt_parts.append(base_text)

        prompt_parts.append("Return only the fragment. No explanations.")
        prompt = "\n".join(prompt_parts)

        try:
            result: LLMResult = await self.llm.generate(prompt)
        except RuntimeError as exc:
            self._log.warning("ollama runtime error: %s", exc)
            return ""
        except Exception as exc:
            self._log.warning("ollama request failed: %s", exc)
            return ""

        if result.used_fallback:
            self._log.info("ollama unavailable; using fallback fragment")
        else:
            self._log.info("ollama response received (%d chars)", len(result.text))

        return result.text

    # ------------------------------------------------------------------
    def _fallback_from_seeds(self, prompt: str) -> str:
        seeds = []
        if self._invitation_fragments:
            seeds.append(random.choice(self._invitation_fragments)["text"])
        if self._journal_fragments:
            seeds.append(random.choice(self._journal_fragments)["text"])
        if self._transcript_fragments:
            seeds.append(random.choice(self._transcript_fragments)["text"])
        collapsed = " / ".join(seeds)
        distilled = self.echo.distill_fragment(collapsed, drift=0.4)
        return distilled or collapsed
