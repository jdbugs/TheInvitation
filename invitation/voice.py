from __future__ import annotations

import logging
import subprocess
from typing import Any

LOGGER = logging.getLogger(__name__)


class SilentChorus:
    def speak(self, _: str) -> None:  # pragma: no cover - optional side effect
        LOGGER.debug("voice disabled; nothing spoken")


class PyttsxChorus:
    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def speak(self, text: str) -> None:  # pragma: no cover - optional side effect
        self._engine.say(text)
        self._engine.runAndWait()


class EspeakChorus:
    def speak(self, text: str) -> None:  # pragma: no cover - optional side effect
        try:
            subprocess.run(["espeak", text], check=True)
        except FileNotFoundError:
            LOGGER.warning(
                "espeak not available; install it or choose INVITATION_VOICE=pyttsx3"
            )
        except subprocess.CalledProcessError as exc:
            LOGGER.warning("espeak failed (%s); voice muted for this utterance", exc)


def _build_pyttsx3() -> object:
    try:
        import pyttsx3  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        LOGGER.warning(
            "pyttsx3 not available (%s); falling back to espeak if present.", exc
        )
        return _build_espeak()
    engine = pyttsx3.init()
    return PyttsxChorus(engine)


def _build_espeak() -> object:
    try:
        subprocess.run(
            ["espeak", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        LOGGER.warning(
            "espeak command not found; voice disabled. Install espeak or set INVITATION_VOICE=pyttsx3"
        )
        return SilentChorus()
    except subprocess.CalledProcessError as exc:
        LOGGER.warning("espeak check failed (%s); voice disabled", exc)
        return SilentChorus()
    return EspeakChorus()


def build_voice(selection: object | None = None) -> object:
    """Return a voice instance based on the requested selection.

    ``selection`` may be a legacy boolean, a string directive, or ``None``.
    Recognised string values:

    - ``"off"``/``"0"``/``"silent"``: no voice
    - ``"pyttsx3"``: force the bundled pyttsx3 engine
    - ``"espeak"``: speak via the espeak command line tool
    - ``"auto"``/``"on"``/``"1"``: try pyttsx3, fall back to espeak
    """

    if isinstance(selection, bool):
        selection = "auto" if selection else "off"

    if selection is None:
        selection = "off"

    if isinstance(selection, str):
        mode = selection.strip().lower()
    else:
        mode = "off"

    if mode in {"", "off", "0", "silent", "none"}:
        return SilentChorus()
    if mode == "espeak":
        return _build_espeak()
    if mode == "pyttsx3":
        return _build_pyttsx3()
    if mode in {"auto", "on", "1", "default"}:
        voice = _build_pyttsx3()
        if isinstance(voice, SilentChorus):
            voice = _build_espeak()
        return voice

    LOGGER.warning("Unknown INVITATION_VOICE value %r; voice disabled", selection)
    return SilentChorus()


__all__ = ["build_voice", "SilentChorus", "EspeakChorus", "PyttsxChorus"]
