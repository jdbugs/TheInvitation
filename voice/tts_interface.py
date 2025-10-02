"""Optional text-to-speech chorus."""
from __future__ import annotations

import logging

LOGGER = logging.getLogger("invitation.voice")


class AmbientChorus:
    """Speaks responses aloud when pyttsx3 is available."""

    def __init__(self) -> None:
        try:
            import pyttsx3  # type: ignore
        except Exception:  # pragma: no cover - optional dependency
            self._engine = None
            LOGGER.info("pyttsx3 not available; chorus silent")
        else:
            self._engine = pyttsx3.init()

    def speak(self, text: str) -> None:
        if not self._engine:
            return
        self._engine.say(text)
        self._engine.runAndWait()

