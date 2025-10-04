from __future__ import annotations

import json
import logging
import random
import re
from pathlib import Path
from typing import Iterable, List

LOGGER = logging.getLogger(__name__)


class FragmentLibrary:
    """Loads text fragments from the project data directory."""

    def __init__(self, data_dir: Path, *, include_journals: bool = False) -> None:
        self._data_dir = data_dir
        self._include_journals = include_journals

    def harvest(self) -> List[str]:
        """Return a shuffled list of textual fragments."""
        fragments: List[str] = []
        fragments.extend(self._from_invitation_text())
        fragments.extend(self._from_transcripts())
        if self._include_journals:
            fragments.extend(self._from_journals())
        filtered = []
        for frag in fragments:
            refined = self._refine_fragment(frag)
            if refined:
                filtered.append(refined)
        random.shuffle(filtered)
        LOGGER.info("library harvested %s fragments", len(filtered))
        return filtered

    def _from_invitation_text(self) -> Iterable[str]:
        target = self._data_dir / "The_Invitation.txt"
        if not target.exists():
            LOGGER.debug("Invitation text not found at %s", target)
            return []
        return self._split_lines(target.read_text(encoding="utf-8"))

    def _from_transcripts(self) -> Iterable[str]:
        target = self._data_dir / "transcripts.txt"
        if not target.exists():
            LOGGER.debug("Transcripts not found at %s", target)
            return []
        return self._split_lines(target.read_text(encoding="utf-8"))

    def _from_journals(self) -> Iterable[str]:
        target = self._data_dir / "journals.json"
        if not target.exists():
            LOGGER.debug("journals.json not found at %s", target)
            return []
        try:
            records = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            LOGGER.warning("Unable to parse journals.json: %s", exc)
            return []
        fragments: List[str] = []
        for record in records:
            text = record.get("text", "")
            fragments.extend(self._split_paragraphs(text))
        return fragments

    @staticmethod
    def _split_lines(blob: str) -> Iterable[str]:
        for line in blob.splitlines():
            candidate = line.strip()
            if candidate:
                yield candidate

    @staticmethod
    def _split_paragraphs(blob: str) -> Iterable[str]:
        for chunk in blob.split("\n\n"):
            candidate = chunk.strip()
            if candidate:
                yield candidate

    @staticmethod
    def _refine_fragment(text: str, *, max_chars: int = 320) -> str:
        cleaned = text.strip()
        if not cleaned:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        collected: List[str] = []
        total = 0
        for sentence in sentences:
            segment = sentence.strip()
            if not segment:
                continue
            projected = total + len(segment)
            if collected:
                projected += 1
            if projected > max_chars:
                break
            collected.append(segment)
            total = projected
            if total >= max_chars:
                break
        if not collected:
            collected_text = cleaned[:max_chars].rstrip()
        else:
            collected_text = " ".join(collected)
        if len(collected_text) < len(cleaned):
            collected_text = collected_text.rstrip(" ,;:") + " …"
        return collected_text
