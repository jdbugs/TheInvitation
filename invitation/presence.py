from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from engine.presence_loop import PresenceEvent, PresenceLoop

LOGGER = logging.getLogger(__name__)


@dataclass
class Utterance:
    speaker: str
    text: str


@dataclass
class PresenceLog:
    limit: int = 6
    utterances: List[Utterance] = field(default_factory=list)

    def record(self, speaker: str, text: str, *, log_event: bool = True) -> None:
        self.utterances.append(Utterance(speaker, text))
        if len(self.utterances) > self.limit:
            self.utterances = self.utterances[-self.limit :]
        if log_event:
            LOGGER.info("heard %s chars", len(text))

    def to_history(self) -> List[dict]:
        return [{"role": u.speaker, "content": u.text} for u in self.utterances]


__all__ = ["PresenceEvent", "PresenceLog", "PresenceLoop"]
