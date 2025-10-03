from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import requests

LOGGER = logging.getLogger(__name__)


class OracleUnavailable(RuntimeError):
    """Raised when the local LLM endpoint cannot be reached."""


@dataclass
class OracleConfig:
    model: str = "llama3.2"
    endpoint: str = "http://localhost:11434"
    temperature: float = 0.4
    timeout: float = 45.0
    min_retry_interval: float = 90.0


class Oracle:
    """Thin HTTP client around an Ollama chat endpoint."""

    def __init__(self, config: OracleConfig) -> None:
        self._config = config
        self._snoozed_until = 0.0

    @property
    def config(self) -> OracleConfig:
        return self._config

    def available(self) -> bool:
        return time.time() >= self._snoozed_until

    def _snooze(self) -> None:
        self._snoozed_until = time.time() + self._config.min_retry_interval

    def chat(self, prompt: str, context: Iterable[Dict[str, str]]) -> str:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not self.available():
            raise OracleUnavailable("oracle in cooldown after earlier failure")

        payload = {
            "model": self._config.model,
            "messages": [*context, {"role": "user", "content": prompt}],
            "options": {"temperature": self._config.temperature},
        }
        url = f"{self._config.endpoint.rstrip('/')}/api/chat"
        try:
            response = requests.post(url, json=payload, timeout=self._config.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("oracle connection failed: %s", exc)
            self._snooze()
            raise OracleUnavailable("oracle connection failed") from exc

        try:
            data = response.json()
        except ValueError as exc:
            LOGGER.warning("oracle returned invalid JSON: %s", exc)
            self._snooze()
            raise OracleUnavailable("oracle produced invalid JSON") from exc

        message = data.get("message") or {}
        content = message.get("content")
        if not content:
            LOGGER.warning(
                "oracle returned no content; response keys: %s", list(data.keys())
            )
            raise OracleUnavailable("oracle produced empty content")
        return content

    def chat_with_system(self, prompt: str, system: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        context: List[Dict[str, str]] = []
        if system:
            context.append({"role": "system", "content": system})
        if history:
            context.extend(history)
        return self.chat(prompt, context)


def default_config() -> OracleConfig:
    return OracleConfig()
