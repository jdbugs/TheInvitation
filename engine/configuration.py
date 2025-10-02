"""Flux configuration architecture for the Invitation engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence
import asyncio
import copy
import json
import logging
import os

LOGGER = logging.getLogger("invitation.config")


@dataclass(frozen=True)
class FieldConfig:
    clip: int = 420
    min_slices: int = 1
    max_slices: int = 4
    base_tags: tuple[str, ...] = ("stillness", "memory", "threshold")
    mutation_rate: float = 0.15


@dataclass(frozen=True)
class ArchitectureConfig:
    name: str
    shard_layers: int
    oracle_bias: float
    echo_prompt: bool = True


@dataclass(frozen=True)
class WeaveConfig:
    max_chars: int = 520
    oracle_weight: float = 0.4
    entangle_bias: float = 0.25
    recursion_bias: float = 0.2
    default_architecture: str = "hybrid"
    architectures: tuple[ArchitectureConfig, ...] = field(
        default_factory=lambda: (
            ArchitectureConfig(name="lattice", shard_layers=3, oracle_bias=0.0, echo_prompt=True),
            ArchitectureConfig(name="hybrid", shard_layers=4, oracle_bias=0.35, echo_prompt=True),
            ArchitectureConfig(name="oracle", shard_layers=2, oracle_bias=1.0, echo_prompt=False),
        )
    )

    def lookup(self, name: str) -> ArchitectureConfig:
        for architecture in self.architectures:
            if architecture.name == name:
                return architecture
        raise KeyError(f"unknown architecture: {name}")


@dataclass(frozen=True)
class PulseConfig:
    min_delay: float = 12.0
    max_delay: float = 48.0
    min_silence: float = 45.0
    max_silence: float = 150.0
    echo_memory: int = 6


@dataclass(frozen=True)
class FeedbackConfig:
    target_chars: int = 320
    tolerance: int = 120
    learning_rate: float = 0.15
    architecture_push: int = 4
    max_layers_ceiling: int = 6
    min_layers_floor: int = 1
    delay_floor: float = 4.0
    delay_ceiling: float = 160.0
    silence_floor: float = 20.0
    silence_ceiling: float = 260.0


@dataclass(frozen=True)
class MetamorphosisConfig:
    window: int = 5
    chaos: float = 0.2
    reactivity: float = 0.25


@dataclass(frozen=True)
class MonitorConfig:
    poll_interval: float = 1.5


@dataclass(frozen=True)
class EngineConfig:
    field: FieldConfig
    weave: WeaveConfig
    pulse: PulseConfig
    feedback: FeedbackConfig
    metamorphosis: MetamorphosisConfig
    monitor: MonitorConfig


_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "field": {
        "clip": FieldConfig().clip,
        "min_slices": FieldConfig().min_slices,
        "max_slices": FieldConfig().max_slices,
        "base_tags": list(FieldConfig().base_tags),
        "mutation_rate": FieldConfig().mutation_rate,
    },
    "weave": {
        "max_chars": WeaveConfig().max_chars,
        "oracle_weight": WeaveConfig().oracle_weight,
        "entangle_bias": WeaveConfig().entangle_bias,
        "recursion_bias": WeaveConfig().recursion_bias,
        "default_architecture": WeaveConfig().default_architecture,
        "architectures": [
            {
                "name": architecture.name,
                "shard_layers": architecture.shard_layers,
                "oracle_bias": architecture.oracle_bias,
                "echo_prompt": architecture.echo_prompt,
            }
            for architecture in WeaveConfig().architectures
        ],
    },
    "pulse": {
        "min_delay": PulseConfig().min_delay,
        "max_delay": PulseConfig().max_delay,
        "min_silence": PulseConfig().min_silence,
        "max_silence": PulseConfig().max_silence,
        "echo_memory": PulseConfig().echo_memory,
    },
    "feedback": {
        "target_chars": FeedbackConfig().target_chars,
        "tolerance": FeedbackConfig().tolerance,
        "learning_rate": FeedbackConfig().learning_rate,
        "architecture_push": FeedbackConfig().architecture_push,
        "max_layers_ceiling": FeedbackConfig().max_layers_ceiling,
        "min_layers_floor": FeedbackConfig().min_layers_floor,
        "delay_floor": FeedbackConfig().delay_floor,
        "delay_ceiling": FeedbackConfig().delay_ceiling,
        "silence_floor": FeedbackConfig().silence_floor,
        "silence_ceiling": FeedbackConfig().silence_ceiling,
    },
    "metamorphosis": {
        "window": MetamorphosisConfig().window,
        "chaos": MetamorphosisConfig().chaos,
        "reactivity": MetamorphosisConfig().reactivity,
    },
    "monitor": {"poll_interval": MonitorConfig().poll_interval},
}


class AdaptiveConfig:
    """Loads the configuration file and streams mutations to listeners."""

    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._listeners: List[Callable[[EngineConfig], None]] = []
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
            LOGGER.debug("no configuration path; watcher idle")
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
                        LOGGER.exception("configuration listener crashed")

    def _reload_if_needed(self) -> bool:
        if not self._path or not self._path.exists():
            return False
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            return False
        if self._mtime is not None and mtime <= self._mtime:
            return False
        self._mtime = mtime
        self._config = self._load()
        LOGGER.info("configuration reloaded from %s", self._path)
        return True

    def _load(self) -> EngineConfig:
        data = copy.deepcopy(_DEFAULTS)
        if self._path and self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                LOGGER.error("failed to parse %s: %s", self._path, error)
            else:
                data = _merge_dicts(data, raw)
        return _coerce(data)


def _merge_dicts(base: Dict[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _merge_dicts(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _coerce(data: Dict[str, Dict[str, Any]]) -> EngineConfig:
    field_conf = FieldConfig(
        clip=max(120, int(data["field"]["clip"])),
        min_slices=max(1, int(data["field"]["min_slices"])),
        max_slices=max(1, int(data["field"]["max_slices"])),
        base_tags=tuple(str(tag).strip() for tag in data["field"].get("base_tags", []) if str(tag).strip()),
        mutation_rate=max(0.0, float(data["field"]["mutation_rate"])),
    )
    architectures = [
        ArchitectureConfig(
            name=str(entry["name"]).strip() or "hybrid",
            shard_layers=max(1, int(entry["shard_layers"])),
            oracle_bias=max(0.0, min(1.0, float(entry["oracle_bias"]))),
            echo_prompt=bool(entry.get("echo_prompt", True)),
        )
        for entry in data["weave"].get("architectures", [])
    ]
    weave_conf = WeaveConfig(
        max_chars=max(120, int(data["weave"]["max_chars"])),
        oracle_weight=max(0.0, min(1.0, float(data["weave"]["oracle_weight"]))),
        entangle_bias=max(0.0, float(data["weave"]["entangle_bias"])),
        recursion_bias=max(0.0, float(data["weave"]["recursion_bias"])),
        default_architecture=str(data["weave"]["default_architecture"]).strip() or "hybrid",
        architectures=tuple(architectures) if architectures else WeaveConfig().architectures,
    )
    pulse_conf = PulseConfig(
        min_delay=max(0.1, float(data["pulse"]["min_delay"])),
        max_delay=max(0.5, float(data["pulse"]["max_delay"])),
        min_silence=max(0.5, float(data["pulse"]["min_silence"])),
        max_silence=max(1.0, float(data["pulse"]["max_silence"])),
        echo_memory=max(1, int(data["pulse"]["echo_memory"])),
    )
    feedback_conf = FeedbackConfig(
        target_chars=max(80, int(data["feedback"]["target_chars"])),
        tolerance=max(20, int(data["feedback"]["tolerance"])),
        learning_rate=max(0.01, float(data["feedback"]["learning_rate"])),
        architecture_push=max(1, int(data["feedback"]["architecture_push"])),
        max_layers_ceiling=max(1, int(data["feedback"]["max_layers_ceiling"])),
        min_layers_floor=max(1, int(data["feedback"]["min_layers_floor"])),
        delay_floor=max(0.1, float(data["feedback"]["delay_floor"])),
        delay_ceiling=max(0.5, float(data["feedback"]["delay_ceiling"])),
        silence_floor=max(0.5, float(data["feedback"]["silence_floor"])),
        silence_ceiling=max(1.0, float(data["feedback"]["silence_ceiling"])),
    )
    metamorph_conf = MetamorphosisConfig(
        window=max(2, int(data["metamorphosis"]["window"])),
        chaos=max(0.0, min(1.0, float(data["metamorphosis"]["chaos"]))),
        reactivity=max(0.0, min(1.0, float(data["metamorphosis"]["reactivity"]))),
    )
    monitor_conf = MonitorConfig(
        poll_interval=max(0.5, float(data["monitor"]["poll_interval"]))
    )
    return EngineConfig(
        field=field_conf,
        weave=weave_conf,
        pulse=pulse_conf,
        feedback=feedback_conf,
        metamorphosis=metamorph_conf,
        monitor=monitor_conf,
    )


def resolve_config_path(base: Path) -> Path | None:
    env = os.environ.get("INVITATION_CONFIG")
    if env:
        candidate = Path(env).expanduser()
        LOGGER.info("using config from %s", candidate)
        return candidate
    candidate = base / "config" / "invitation.json"
    return candidate if candidate.exists() else None


def apply_listeners(config: AdaptiveConfig, listeners: Iterable[Callable[[EngineConfig], None]]) -> None:
    for listener in listeners:
        config.add_listener(listener)
