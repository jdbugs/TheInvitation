"""Response composition."""
from __future__ import annotations

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

    async def craft(self, *, user_text: str | None, channel: str) -> Response:
        fragments = tuple(_unique_fragments(self._library.pick(self._config.fragments)))
        oracle_text = None
        use_oracle = self._oracle.enabled and self._rng.random() < self._config.oracle_probability
        if use_oracle:
            prompt = self._prompt(user_text, channel, fragments)
            oracle_text = await self._oracle.generate(prompt)
            if oracle_text:
                LOGGER.debug("oracle contributed %d chars", len(oracle_text))
        body = self._assemble(user_text, channel, fragments, oracle_text)
        return Response(
            text=body,
            channel=channel,
            fragments=fragments,
            used_oracle=bool(oracle_text),
        )

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
        if oracle is not None:
            self._oracle = oracle

    def _assemble(
        self,
        user_text: str | None,
        channel: str,
        fragments: Iterable[SeedFragment],
        oracle_text: str | None,
    ) -> str:
        pieces: list[str] = []
        opening = self._opening_line(user_text, channel)
        if opening:
            pieces.append(opening)
        for fragment in fragments:
            text = fragment.text.strip()
            if text:
                pieces.append(text)
        if oracle_text and oracle_text.strip():
            pieces.append(oracle_text.strip())
        closing = self._config.closing_line.strip()
        if closing and (not pieces or pieces[-1] != closing):
            pieces.append(closing)
        combined = "\n\n".join(piece for piece in pieces if piece)
        return _clip(combined, self._config.max_chars)

    def _opening_line(self, user_text: str | None, channel: str) -> str:
        if channel == "silence":
            return "The room stays open."
        if self._config.echo_user and user_text:
            return f"You said: {user_text.strip()}"
        return self._config.opening_line.strip()

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
