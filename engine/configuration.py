"""Adaptive configuration loader for the Invitation engine."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable
import asyncio
import json
import logging
import os
import copy

LOGGER = logging.getLogger("invitation.config")


@dataclass(frozen=True)
class AtlasConfig:
    clip: int = 360


@dataclass(frozen=True)
class ComposerConfig:
    max_layers: int = 3
    max_chars: int = 560
    architecture: str = "hybrid"
    oracle_weight: float = 0.4


@dataclass(frozen=True)
class ObserverConfig:
    min_delay: float = 12.0
    max_delay: float = 48.0
    min_silence: float = 45.0
    max_silence: float = 120.0
    echo_memory: int = 6


@dataclass(frozen=True)
class FeedbackConfig:
    target_length: int = 240
    tolerance: int = 60
    adjust_rate: float = 0.15
    architecture_shift: int = 4
    max_layers_ceiling: int = 5
    min_layers_floor: int = 1
    delay_floor: float = 4.0
    delay_ceiling: float = 120.0
    silence_floor: float = 20.0
    silence_ceiling: float = 240.0


@dataclass(frozen=True)
class MonitorConfig:
    poll_interval: float = 5.0


@dataclass(frozen=True)
class EngineConfig:
    atlas: AtlasConfig
    composer: ComposerConfig
    observer: ObserverConfig
    feedback: FeedbackConfig
    monitor: MonitorConfig


_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "atlas": {"clip": AtlasConfig().clip},
    "composer": {
        "max_layers": ComposerConfig().max_layers,
        "max_chars": ComposerConfig().max_chars,
        "architecture": ComposerConfig().architecture,
        "oracle_weight": ComposerConfig().oracle_weight,
    },
    "observer": {
        "min_delay": ObserverConfig().min_delay,
        "max_delay": ObserverConfig().max_delay,
        "min_silence": ObserverConfig().min_silence,
        "max_silence": ObserverConfig().max_silence,
        "echo_memory": ObserverConfig().echo_memory,
    },
    "feedback": {
        "target_length": FeedbackConfig().target_length,
        "tolerance": FeedbackConfig().tolerance,
        "adjust_rate": FeedbackConfig().adjust_rate,
        "architecture_shift": FeedbackConfig().architecture_shift,
        "max_layers_ceiling": FeedbackConfig().max_layers_ceiling,
        "min_layers_floor": FeedbackConfig().min_layers_floor,
        "delay_floor": FeedbackConfig().delay_floor,
        "delay_ceiling": FeedbackConfig().delay_ceiling,
        "silence_floor": FeedbackConfig().silence_floor,
        "silence_ceiling": FeedbackConfig().silence_ceiling,
    },
    "monitor": {"poll_interval": MonitorConfig().poll_interval},
}


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


class AdaptiveConfig:
    """Loads configuration and notifies listeners when it changes."""

    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._listeners: list[Callable[[EngineConfig], None]] = []
        self._config = self._load()
        self._mtime = self._path.stat().st_mtime if self._path and self._path.exists() else None

    @property
    def path(self) -> Path | None:
        return self._path

    def snapshot(self) -> EngineConfig:
        return self._config

    def add_listener(self, listener: Callable[[EngineConfig], None]) -> None:
        self._listeners.append(listener)

    async def watch(self, interval: float | None = None) -> None:
        if not self._path:
            LOGGER.debug("no config path supplied; watcher idle")
            return
        poll = interval or self._config.monitor.poll_interval
        while True:
            await asyncio.sleep(max(0.5, poll))
            if self._reload_if_needed():
                snapshot = self._config
                poll = interval or snapshot.monitor.poll_interval
                for listener in list(self._listeners):
                    try:
                        listener(snapshot)
                    except Exception:
                        LOGGER.exception("config listener crashed")

    def _reload_if_needed(self) -> bool:
        if not self._path or not self._path.exists():
            return False
        try:
            current = self._path.stat().st_mtime
        except OSError:
            return False
        if self._mtime is not None and current <= self._mtime:
            return False
        self._mtime = current
        self._config = self._load()
        LOGGER.info("configuration reloaded from %s", self._path)
        return True

    def _load(self) -> EngineConfig:
        data = copy.deepcopy(_DEFAULTS)
        if self._path and self._path.exists():
            try:
                file_data = json.loads(self._path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                LOGGER.error("failed to parse %s: %s", self._path, error)
            else:
                data = _merge_dict(data, file_data)
        return _coerce(data)


def _coerce(raw: Dict[str, Dict[str, Any]]) -> EngineConfig:
    atlas = AtlasConfig(clip=int(raw["atlas"]["clip"]))
    composer = ComposerConfig(
        max_layers=max(1, int(raw["composer"]["max_layers"])),
        max_chars=max(80, int(raw["composer"]["max_chars"])),
        architecture=str(raw["composer"]["architecture"]).strip() or "hybrid",
        oracle_weight=max(0.0, min(1.0, float(raw["composer"]["oracle_weight"]))),
    )
    observer = ObserverConfig(
        min_delay=float(raw["observer"]["min_delay"]),
        max_delay=float(raw["observer"]["max_delay"]),
        min_silence=float(raw["observer"]["min_silence"]),
        max_silence=float(raw["observer"]["max_silence"]),
        echo_memory=max(1, int(raw["observer"]["echo_memory"])),
    )
    feedback = FeedbackConfig(
        target_length=max(40, int(raw["feedback"]["target_length"])),
        tolerance=max(20, int(raw["feedback"]["tolerance"])),
        adjust_rate=max(0.01, float(raw["feedback"]["adjust_rate"])),
        architecture_shift=max(1, int(raw["feedback"]["architecture_shift"])),
        max_layers_ceiling=max(1, int(raw["feedback"]["max_layers_ceiling"])),
        min_layers_floor=max(1, int(raw["feedback"]["min_layers_floor"])),
        delay_floor=max(0.1, float(raw["feedback"]["delay_floor"])),
        delay_ceiling=max(0.5, float(raw["feedback"]["delay_ceiling"])),
        silence_floor=max(0.5, float(raw["feedback"]["silence_floor"])),
        silence_ceiling=max(1.0, float(raw["feedback"]["silence_ceiling"])),
    )
    monitor = MonitorConfig(poll_interval=max(0.5, float(raw["monitor"]["poll_interval"])))
    return EngineConfig(
        atlas=atlas,
        composer=composer,
        observer=observer,
        feedback=feedback,
        monitor=monitor,
    )


def resolve_config_path(base: Path) -> Path | None:
    """Determine which config file to load."""
    env = os.environ.get("INVITATION_CONFIG")
    if env:
        path = Path(env).expanduser()
        LOGGER.info("using config from %s", path)
        return path
    candidate = base / "config" / "invitation.json"
    if candidate.exists():
        return candidate
    return None


def apply_listeners(config: AdaptiveConfig, listeners: Iterable[Callable[[EngineConfig], None]]) -> None:
    for listener in listeners:
        config.add_listener(listener)
