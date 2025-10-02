"""Optional text-to-speech chorus."""
from __future__ import annotations

import logging

LOGGER = logging.getLogger("invitation.voice")


class AmbientChorus:
    """Speaks responses aloud when pyttsx3 is available."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        voice: str | None = None,
        rate: int | None = None,
        volume: float | None = None,
    ) -> None:
        self._engine = None
        self._enabled = enabled
        if not enabled:
            LOGGER.info("chorus disabled via configuration")
            return
        try:
            import pyttsx3  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            LOGGER.warning(
                "pyttsx3 not available; chorus silent (import error: %s)",
                exc,
                exc_info=True,
            )
            LOGGER.warning(
                "install pyttsx3 in the same interpreter you use for main.py; "
                "Python 3.13 users may need `pip install pyttsx3==2.90`"
            )
            self._enabled = False
        else:
            engine = pyttsx3.init()
            if voice:
                try:
                    engine.setProperty("voice", voice)
                except Exception:  # pragma: no cover - defensive guard
                    LOGGER.warning("failed to set voice %s", voice)
            if rate:
                try:
                    engine.setProperty("rate", int(rate))
                except Exception:  # pragma: no cover
                    LOGGER.warning("failed to set rate %s", rate)
            if volume is not None:
                try:
                    engine.setProperty("volume", max(0.0, min(1.0, float(volume))))
                except Exception:  # pragma: no cover
                    LOGGER.warning("failed to set volume %s", volume)
            self._engine = engine

    @property
    def enabled(self) -> bool:
        return bool(self._engine) and self._enabled

    def speak(self, text: str) -> None:
        if not self.enabled:
            return
        self._engine.say(text)
        self._engine.runAndWait()

