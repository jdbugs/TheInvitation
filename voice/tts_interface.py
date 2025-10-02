"""Optional ambient text-to-speech support."""
from __future__ import annotations

import asyncio
from typing import Optional

try:
    import importlib
    _pyttsx3_spec = importlib.util.find_spec("pyttsx3")  # type: ignore[attr-defined]
    if _pyttsx3_spec is not None:
        import pyttsx3  # type: ignore
    else:
        pyttsx3 = None  # type: ignore
except Exception:  # pragma: no cover - import failure fallback
    pyttsx3 = None  # type: ignore


class AmbientTTS:
    """Thin wrapper around pyttsx3 if available."""

    def __init__(self, enabled: bool = False, rate: int = 140) -> None:
        self.enabled = enabled and pyttsx3 is not None
        self._rate = rate
        self._engine: Optional["pyttsx3.Engine"] = None

    async def speak(self, text: str) -> None:
        if not self.enabled or not text.strip():
            return
        await asyncio.to_thread(self._speak_sync, text)

    # ------------------------------------------------------------------
    def _ensure_engine(self) -> Optional["pyttsx3.Engine"]:
        if pyttsx3 is None:
            return None
        if self._engine is None:
            self._engine = pyttsx3.init()  # type: ignore[call-arg]
            self._engine.setProperty("rate", self._rate)
            self._engine.setProperty("volume", 0.6)
        return self._engine

    def _speak_sync(self, text: str) -> None:
        engine = self._ensure_engine()
        if engine is None:
            return
        engine.say(text)
        engine.runAndWait()
