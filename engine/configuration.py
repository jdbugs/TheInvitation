"""Configuration utilities for the Invitation prototype."""
from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Callable, Dict
import asyncio
import json
import logging
import os

LOGGER = logging.getLogger("invitation.config")


@dataclass(frozen=True)
class LibraryConfig:
    clip_chars: int = 320
    min_words: int = 6
    max_fragments: int = 3


@dataclass(frozen=True)
class ResponseConfig:
    max_chars: int = 360
    fragments: int = 2
    oracle_probability: float = 0.4
    echo_user: bool = True
    opening_line: str = "I hear you."
    closing_line: str = "Stay with the quiet."


@dataclass(frozen=True)
class TimingConfig:
    min_delay: float = 6.0
    max_delay: float = 18.0
    min_silence: float = 24.0
    max_silence: float = 60.0
    echo_memory: int = 6


@dataclass(frozen=True)
class FeedbackConfig:
    target_chars: int = 240
    tolerance: int = 80


@dataclass(frozen=True)
class OracleConfig:
    enabled: bool = True
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2"
    timeout: float = 12.0


@dataclass(frozen=True)
class VoiceConfig:
    enabled: bool = True
    voice: str | None = None
    rate: int | None = None
    volume: float | None = None


@dataclass(frozen=True)
class OutputConfig:
    show_debug: bool = False
    prefix: str = "— invitation —"


@dataclass(frozen=True)
class MonitorConfig:
    poll_interval: float = 1.5


@dataclass(frozen=True)
class EngineConfig:
    library: LibraryConfig
    response: ResponseConfig
    timing: TimingConfig
    feedback: FeedbackConfig
    oracle: OracleConfig
    voice: VoiceConfig
    output: OutputConfig
    monitor: MonitorConfig


_DEFAULT = EngineConfig(
    library=LibraryConfig(),
    response=ResponseConfig(),
    timing=TimingConfig(),
    feedback=FeedbackConfig(),
    oracle=OracleConfig(),
    voice=VoiceConfig(),
    output=OutputConfig(),
    monitor=MonitorConfig(),
)


def resolve_config_path(base: Path) -> Path | None:
    """Return the config path if it exists, otherwise ``None``."""

    env_path = os.environ.get("INVITATION_CONFIG")
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate
        LOGGER.warning("INVITATION_CONFIG=%s does not exist; falling back to defaults", candidate)
    candidate = base / "config" / "invitation.json"
    if candidate.exists():
        return candidate
    return None


def _coerce(dataclass_type: type, payload: Dict[str, Any] | None) -> Any:
    if payload is None:
        payload = {}
    valid_fields = {field.name for field in fields(dataclass_type)}
    filtered: Dict[str, Any] = {}
    for key, value in payload.items():
        if key in valid_fields and value is not None:
            filtered[key] = value
    try:
        return dataclass_type(**filtered)
    except TypeError:
        LOGGER.warning("ignoring incompatible configuration values for %s", dataclass_type.__name__)
        return dataclass_type()


def _load_payload(path: Path | None) -> Dict[str, Any]:
    if path is None:
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        LOGGER.warning("configuration file %s disappeared; falling back to defaults", path)
    except json.JSONDecodeError as exc:
        LOGGER.error("failed to parse %s: %s", path, exc)
    return {}


def parse_config(path: Path | None) -> EngineConfig:
    payload = _load_payload(path)
    return EngineConfig(
        library=_coerce(LibraryConfig, payload.get("library")),
        response=_coerce(ResponseConfig, payload.get("response")),
        timing=_coerce(TimingConfig, payload.get("timing")),
        feedback=_coerce(FeedbackConfig, payload.get("feedback")),
        oracle=_coerce(OracleConfig, payload.get("oracle")),
        voice=_coerce(VoiceConfig, payload.get("voice")),
        output=_coerce(OutputConfig, payload.get("output")),
        monitor=_coerce(MonitorConfig, payload.get("monitor")),
    )


class AdaptiveConfig:
    """Load the config file once and optionally watch for changes."""

    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._config = parse_config(path) if path else _DEFAULT
        self._listeners: list[Callable[[EngineConfig], None]] = []
        self._mtime = self._stat_mtime()
        self._lock = asyncio.Lock()

    @property
    def path(self) -> Path | None:
        return self._path

    def snapshot(self) -> EngineConfig:
        return self._config

    def add_listener(self, listener: Callable[[EngineConfig], None]) -> None:
        self._listeners.append(listener)

    async def watch(self) -> None:
        if self._path is None:
            return
        while True:
            await asyncio.sleep(self._config.monitor.poll_interval)
            async with self._lock:
                mtime = self._stat_mtime()
                if mtime is None or mtime == self._mtime:
                    continue
                new_config = parse_config(self._path)
                self._config = new_config
                self._mtime = mtime
                LOGGER.info("configuration reloaded from %s", self._path)
                for listener in list(self._listeners):
                    try:
                        listener(new_config)
                    except Exception as exc:  # pragma: no cover - defensive
                        LOGGER.exception("configuration listener failed: %s", exc)

    def _stat_mtime(self) -> float | None:
        if self._path is None or not self._path.exists():
            return None
        return self._path.stat().st_mtime


__all__ = [
    "AdaptiveConfig",
    "EngineConfig",
    "FeedbackConfig",
    "LibraryConfig",
    "MonitorConfig",
    "OracleConfig",
    "OutputConfig",
    "ResponseConfig",
    "TimingConfig",
    "VoiceConfig",
    "parse_config",
    "resolve_config_path",
]
