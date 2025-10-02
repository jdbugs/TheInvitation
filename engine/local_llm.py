"""Interface for interacting with a local Ollama model with graceful fallbacks."""
from __future__ import annotations

import asyncio
import json
import os
import random
from dataclasses import dataclass
from typing import Callable, Optional
import http.client


@dataclass
class LLMResult:
    """Container for results returned by :class:`LocalLLM`."""

    text: str
    used_fallback: bool = False
    model: Optional[str] = None


class LocalLLM:
    """Lightweight asynchronous wrapper around the Ollama HTTP API.

    The class attempts to reach a running Ollama instance. If it fails, it will
    fall back to a provided callable that can produce simulated output.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        host: str = "127.0.0.1",
        port: int = 11434,
        temperature: float = 0.65,
        timeout: float = 60.0,
        fallback: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.model = model
        self.host = host
        self.port = port
        self.temperature = temperature
        self.timeout = timeout
        self.fallback = fallback if fallback is not None else self.default_fallback

    async def generate(self, prompt: str, max_tokens: int = 120) -> LLMResult:
        """Generate a completion asynchronously.

        Parameters
        ----------
        prompt:
            Prompt text to provide to the local model.
        max_tokens:
            Upper bound on tokens to request from Ollama.
        """

        try:
            text = await asyncio.wait_for(
                asyncio.to_thread(self._request, prompt, max_tokens),
                timeout=self.timeout,
            )
            return LLMResult(text=text.strip(), used_fallback=False, model=self.model)
        except Exception:
            simulated = self.fallback(prompt)
            return LLMResult(text=simulated.strip(), used_fallback=True, model=self.model)

    # ------------------------------------------------------------------
    def _request(self, prompt: str, max_tokens: int) -> str:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": max_tokens,
                },
                "stream": False,
            }
        )
        try:
            conn.request(
                "POST",
                "/api/generate",
                body=payload,
                headers={"Content-Type": "application/json"},
            )
            response = conn.getresponse()
            if response.status >= 400:
                raise RuntimeError(f"Ollama error {response.status}: {response.read().decode('utf-8', 'ignore')}")
            raw_body = response.read()
            if not raw_body:
                return ""
            data = json.loads(raw_body.decode("utf-8"))
            text = data.get("response") or ""
            return text
        finally:
            conn.close()

    # ------------------------------------------------------------------
    def set_fallback(self, func: Callable[[str], str]) -> None:
        """Attach or replace the fallback generator."""

        self.fallback = func

    # ------------------------------------------------------------------
    def default_fallback(self, prompt: str) -> str:
        """Very small deterministic fallback used when no callable is provided."""

        random.seed(hash(prompt) ^ hash(os.getpid()))
        fragments = [
            "the echo leans back into the dark",
            "absence hums at the edge of the request",
            "nothing answers, and that is still an answer",
        ]
        return random.choice(fragments)
