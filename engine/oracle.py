"""Optional oracle client — whispers from a local Ollama instance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import asyncio
import json
import logging
import os
import urllib.error
import urllib.request

LOGGER = logging.getLogger("invitation.oracle")


@dataclass(frozen=True)
class OracleSettings:
    base_url: str
    model: str
    enabled: bool


class OracleClient:
    """A dependency-light async wrapper around the Ollama HTTP API."""

    def __init__(self, settings: OracleSettings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    @classmethod
    def from_env(cls) -> "OracleClient":
        disable = os.environ.get("INVITATION_DISABLE_LLM", "0").lower() in {"1", "true", "yes"}
        if disable:
            return cls.disabled()
        base_url = os.environ.get("INVITATION_OLLAMA_URL", "http://localhost:11434")
        model = os.environ.get("INVITATION_MODEL", "llama3.2")
        LOGGER.info("oracle primed for %s via %s", model, base_url)
        return cls(OracleSettings(base_url=base_url, model=model, enabled=True))

    @classmethod
    def disabled(cls) -> "OracleClient":
        return cls(OracleSettings(base_url="", model="", enabled=False))

    async def dream(self, prompt: str) -> str | None:
        if not self.enabled:
            return None
        payload = json.dumps({"model": self._settings.model, "prompt": prompt, "stream": False}).encode("utf-8")
        request = urllib.request.Request(
            f"{self._settings.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        loop = asyncio.get_running_loop()
        try:
            raw = await loop.run_in_executor(None, self._execute, request)
        except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover - I/O failures
            LOGGER.warning("oracle connection failed: %s", exc)
            return None
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception("oracle raised unexpected error: %s", exc)
            return None
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("oracle returned non-JSON payload")
            return None
        text = payload.get("response") or payload.get("text") or ""
        return text.strip() or None

    @staticmethod
    def _execute(request: urllib.request.Request) -> bytes:
        with urllib.request.urlopen(request, timeout=12) as response:  # nosec B310 (local endpoint)
            return response.read()


__all__ = ["OracleClient", "OracleSettings"]
