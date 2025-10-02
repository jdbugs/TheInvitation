"""Optional oracle client that talks to Ollama."""
from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json
import logging
import urllib.error
import urllib.request

from .configuration import OracleConfig

LOGGER = logging.getLogger("invitation.oracle")


@dataclass(frozen=True)
class OracleSettings:
    base_url: str
    model: str
    enabled: bool
    timeout: float


class OracleClient:
    def __init__(self, settings: OracleSettings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    @classmethod
    def from_config(cls, config: OracleConfig) -> "OracleClient":
        if not config.enabled:
            LOGGER.info("oracle disabled via configuration")
            return cls.disabled()
        LOGGER.info("oracle primed for %s via %s", config.model, config.base_url)
        return cls(
            OracleSettings(
                base_url=config.base_url,
                model=config.model,
                enabled=True,
                timeout=config.timeout,
            )
        )

    @classmethod
    def disabled(cls) -> "OracleClient":
        return cls(OracleSettings(base_url="", model="", enabled=False, timeout=0.0))

    async def generate(self, prompt: str) -> str | None:
        if not self.enabled:
            return None
        payload = json.dumps(
            {
                "model": self._settings.model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self._settings.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        loop = asyncio.get_running_loop()
        try:
            raw = await loop.run_in_executor(None, self._execute, request, self._settings.timeout)
        except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover - network errors
            LOGGER.warning("oracle connection failed: %s", exc)
            return None
        except Exception as exc:  # pragma: no cover - defensive
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
    def _execute(request: urllib.request.Request, timeout: float) -> bytes:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            return response.read()


__all__ = ["OracleClient", "OracleSettings"]
