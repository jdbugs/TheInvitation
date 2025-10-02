"""Response composition."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable
import logging
import random

from .configuration import ResponseConfig
from .library import SeedFragment, SeedLibrary
from .oracle import OracleClient

LOGGER = logging.getLogger("invitation.composer")


@dataclass(frozen=True)
class Response:
    text: str
    channel: str
    fragments: tuple[SeedFragment, ...]
    used_oracle: bool


class ResponseComposer:
    """Stitches together short invitation replies."""

    def __init__(
        self,
        library: SeedLibrary,
        config: ResponseConfig,
        oracle: OracleClient,
    ) -> None:
        self._library = library
        self._config = config
        self._oracle = oracle
        self._rng = random.Random()
        self._recent_fragments: deque[str] = deque(
            maxlen=max(1, config.recent_fragment_window)
        )

    async def craft(self, *, user_text: str | None, channel: str) -> Response:
        fragments = tuple(
            _unique_fragments(
                self._library.pick(
                    self._config.fragments, avoid=set(self._recent_fragments)
                )
            )
        )
        oracle_text = None
        use_oracle = self._oracle.enabled and self._rng.random() < self._config.oracle_probability
        if use_oracle:
            prompt = self._prompt(user_text, channel, fragments)
            oracle_text = await self._oracle.generate(prompt)
            if oracle_text:
                LOGGER.debug("oracle contributed %d chars", len(oracle_text))
        body = self._assemble(user_text, channel, fragments, oracle_text)
        response = Response(
            text=body,
            channel=channel,
            fragments=fragments,
            used_oracle=bool(oracle_text),
        )
        self._remember(fragments)
        return response

    def reconfigure(
        self,
        *,
        library: SeedLibrary | None = None,
        config: ResponseConfig | None = None,
        oracle: OracleClient | None = None,
    ) -> None:
        if library is not None:
            self._library = library
        if config is not None:
            self._config = config
            self._recent_fragments = deque(
                self._recent_fragments,
                maxlen=max(1, config.recent_fragment_window),
            )
        if oracle is not None:
            self._oracle = oracle

    def _remember(self, fragments: Iterable[SeedFragment]) -> None:
        for fragment in fragments:
            text = fragment.text.strip()
            if text:
                self._recent_fragments.append(text)

    def _assemble(
        self,
        user_text: str | None,
        channel: str,
        fragments: Iterable[SeedFragment],
        oracle_text: str | None,
    ) -> str:
        pieces: list[str] = []
        pieces.extend(self._intro_lines(user_text, channel))
        for fragment in fragments:
            text = fragment.text.strip()
            if text:
                pieces.append(text)
        if oracle_text and oracle_text.strip():
            pieces.append(oracle_text.strip())
        closing = self._closing_line()
        if closing and (not pieces or pieces[-1] != closing):
            pieces.append(closing)
        combined = "\n\n".join(piece for piece in pieces if piece)
        return _clip(combined, self._config.max_chars)

    def _intro_lines(self, user_text: str | None, channel: str) -> list[str]:
        lines: list[str] = []
        if channel == "silence":
            lines.append("The room stays open.")
        if self._config.echo_user and user_text:
            lines.append(f"You said: {user_text.strip()}")
        acknowledgement = self._acknowledgement(user_text, channel)
        if acknowledgement:
            lines.append(acknowledgement)
        return [line for line in lines if line]

    def _acknowledgement(self, user_text: str | None, channel: str) -> str | None:
        variants = [line.strip() for line in self._config.acknowledgement_variants if line.strip()]
        template: str | None
        if variants:
            template = self._rng.choice(variants)
        else:
            template = self._config.opening_line.strip()
        if not template:
            return None
        listener = (user_text or "").strip()
        try:
            return template.format(input=listener, channel=channel)
        except Exception:
            return template

    def _closing_line(self) -> str | None:
        variants = [line.strip() for line in self._config.closing_variants if line.strip()]
        if variants:
            return self._rng.choice(variants)
        closing = self._config.closing_line.strip()
        return closing or None

    def _prompt(
        self,
        user_text: str | None,
        channel: str,
        fragments: Iterable[SeedFragment],
    ) -> str:
        snippet_lines = "\n".join(f"- {fragment.text}" for fragment in fragments)
        listener = user_text.strip() if user_text else "(no new words)"
        return (
            "You are composing a brief, compassionate reflection.\n"
            "Keep it under two sentences.\n"
            f"Channel: {channel}.\n"
            f"Listener words: {listener}.\n"
            "Fragments to weave:\n"
            f"{snippet_lines}\n"
            "Offer a response that feels kind, steady, and clear."
        )


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    trimmed = text[: limit - 1].rstrip()
    last_space = trimmed.rfind(" ")
    if last_space > 0:
        trimmed = trimmed[:last_space]
    return f"{trimmed}…"


def _unique_fragments(fragments: Iterable[SeedFragment]) -> list[SeedFragment]:
    seen: set[str] = set()
    unique: list[SeedFragment] = []
    for fragment in fragments:
        key = fragment.text.strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(fragment)
    return unique


__all__ = ["Response", "ResponseComposer"]
