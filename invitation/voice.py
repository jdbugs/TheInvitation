from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


class SilentChorus:
    def speak(self, _: str) -> None:  # pragma: no cover - optional side effect
        LOGGER.debug("voice disabled; nothing spoken")


class PyttsxChorus:
    def __init__(self, engine) -> None:
        self._engine = engine

    def speak(self, text: str) -> None:  # pragma: no cover - optional side effect
        self._engine.say(text)
        self._engine.runAndWait()


def build_voice(enabled: bool) -> object:
    if not enabled:
        return SilentChorus()
    try:
        import pyttsx3  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        LOGGER.warning(
            "pyttsx3 not available (%s); chorus silent. Install with `pip install pyttsx3==2.90` using the same interpreter as main.py.",
            exc,
        )
        return SilentChorus()
    engine = pyttsx3.init()
    return PyttsxChorus(engine)
