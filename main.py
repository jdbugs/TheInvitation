"""Entry point for the Invitation prototype."""
from __future__ import annotations

from pathlib import Path
import asyncio
import contextlib
import logging
import os

from engine.composer import ResponseComposer
from engine.configuration import (
    AdaptiveConfig,
    EngineConfig,
    TimingConfig,
    resolve_config_path,
)
from engine.library import SeedLibrary
from engine.oracle import OracleClient
from engine.presence import LoopSettings, PresenceLoop
from ui.terminal_display import TerminalPortal
from voice.tts_interface import AmbientChorus

LOGGER = logging.getLogger("invitation.main")


def _configure_logging() -> None:
    level = os.environ.get("INVITATION_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _scale_timing(timing: TimingConfig) -> TimingConfig:
    try:
        scale = float(os.environ.get("INVITATION_TIME_SCALE", "1.0"))
    except ValueError:
        scale = 1.0
    if scale <= 0:
        return timing
    return TimingConfig(
        min_delay=timing.min_delay * scale,
        max_delay=timing.max_delay * scale,
        min_silence=timing.min_silence * scale,
        max_silence=timing.max_silence * scale,
        echo_memory=timing.echo_memory,
    )


def _build_chorus(config) -> AmbientChorus | None:
    if not config.enabled:
        return None
    chorus = AmbientChorus(
        enabled=config.enabled,
        voice=config.voice,
        rate=config.rate,
        volume=config.volume,
    )
    return chorus if chorus.enabled else None


def _build_oracle(config) -> OracleClient:
    return OracleClient.from_config(config)


async def main() -> None:
    _configure_logging()
    base = Path(__file__).parent
    config_path = resolve_config_path(base)
    adaptive = AdaptiveConfig(config_path)
    config = adaptive.snapshot()

    library = SeedLibrary.from_path(base / "data", config.library)
    oracle = _build_oracle(config.oracle)
    composer = ResponseComposer(library, config.response, oracle)
    chorus = _build_chorus(config.voice)
    portal = TerminalPortal(
        prefix=config.output.prefix,
        show_debug=config.output.show_debug,
        chorus=chorus,
    )
    loop = PresenceLoop(
        composer,
        portal,
        LoopSettings(
            timing=_scale_timing(config.timing),
            feedback=config.feedback,
        ),
    )

    current_config = config

    def apply(update: EngineConfig) -> None:
        nonlocal library, oracle, current_config
        if update.library != current_config.library:
            library = SeedLibrary.from_path(base / "data", update.library)
        if update.oracle != current_config.oracle:
            oracle = _build_oracle(update.oracle)
        composer.reconfigure(
            library=library,
            config=update.response,
            oracle=oracle,
        )
        new_chorus = _build_chorus(update.voice)
        portal.apply_surface(
            prefix=update.output.prefix,
            show_debug=update.output.show_debug,
            chorus=new_chorus,
        )
        loop.apply(
            timing=_scale_timing(update.timing),
            feedback=update.feedback,
        )
        current_config = update
        LOGGER.info("configuration applied")

    adaptive.add_listener(apply)
    watcher_task: asyncio.Task | None = None
    if adaptive.path:
        watcher_task = asyncio.create_task(adaptive.watch())

    try:
        await loop.run()
    finally:
        if watcher_task is not None:
            watcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
