"""Entry point for the Invitation prototype."""
from __future__ import annotations

from pathlib import Path
import asyncio
import logging
import os
import contextlib

from engine.aurora import AuroraWeave
from engine.constellation import ConstellationAtlas
from engine.configuration import AdaptiveConfig, EngineConfig, resolve_config_path
from engine.observer import FeedbackSettings, ObserverSettings, ThresholdObserver
from engine.oracle import OracleClient
from ui.terminal_display import TerminalPortal


LOGGER = logging.getLogger("invitation.main")


def _configure_logging() -> None:
    level = os.environ.get("INVITATION_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _time_scaled(settings: ObserverSettings) -> ObserverSettings:
    scale = float(os.environ.get("INVITATION_TIME_SCALE", "1.0"))
    if scale <= 0:
        return settings
    return ObserverSettings(
        min_delay=settings.min_delay * scale,
        max_delay=settings.max_delay * scale,
        min_silence=settings.min_silence * scale,
        max_silence=settings.max_silence * scale,
        echo_memory=settings.echo_memory,
    )


async def main() -> None:
    _configure_logging()
    base = Path(__file__).parent
    config_path = resolve_config_path(base)
    adaptive = AdaptiveConfig(config_path)
    snapshot = adaptive.snapshot()

    atlas = ConstellationAtlas.from_data_dir(base / "data", clip=snapshot.atlas.clip)
    oracle = OracleClient.from_env()
    weave = AuroraWeave(
        atlas,
        oracle=oracle,
        max_layers=snapshot.composer.max_layers,
        max_chars=snapshot.composer.max_chars,
        architecture=snapshot.composer.architecture,
        oracle_weight=snapshot.composer.oracle_weight,
    )
    display = TerminalPortal()
    observer = ThresholdObserver(
        weave,
        display,
        settings=_time_scaled(
            ObserverSettings(
                min_delay=snapshot.observer.min_delay,
                max_delay=snapshot.observer.max_delay,
                min_silence=snapshot.observer.min_silence,
                max_silence=snapshot.observer.max_silence,
                echo_memory=snapshot.observer.echo_memory,
            )
        ),
        feedback=FeedbackSettings(
            target_length=snapshot.feedback.target_length,
            tolerance=snapshot.feedback.tolerance,
            adjust_rate=snapshot.feedback.adjust_rate,
            architecture_shift=snapshot.feedback.architecture_shift,
            max_layers_ceiling=snapshot.feedback.max_layers_ceiling,
            min_layers_floor=snapshot.feedback.min_layers_floor,
            delay_floor=snapshot.feedback.delay_floor,
            delay_ceiling=snapshot.feedback.delay_ceiling,
            silence_floor=snapshot.feedback.silence_floor,
            silence_ceiling=snapshot.feedback.silence_ceiling,
        ),
    )

    current_config = snapshot

    def apply(update: EngineConfig) -> None:
        nonlocal atlas, current_config
        if update.atlas.clip != current_config.atlas.clip:
            atlas = ConstellationAtlas.from_data_dir(base / "data", clip=update.atlas.clip)
            weave.set_atlas(atlas)
        weave.reconfigure(
            max_layers=update.composer.max_layers,
            max_chars=update.composer.max_chars,
            architecture=update.composer.architecture,
            oracle_weight=update.composer.oracle_weight,
        )
        observer.apply_config(
            _time_scaled(
                ObserverSettings(
                    min_delay=update.observer.min_delay,
                    max_delay=update.observer.max_delay,
                    min_silence=update.observer.min_silence,
                    max_silence=update.observer.max_silence,
                    echo_memory=update.observer.echo_memory,
                )
            ),
            FeedbackSettings(
                target_length=update.feedback.target_length,
                tolerance=update.feedback.tolerance,
                adjust_rate=update.feedback.adjust_rate,
                architecture_shift=update.feedback.architecture_shift,
                max_layers_ceiling=update.feedback.max_layers_ceiling,
                min_layers_floor=update.feedback.min_layers_floor,
                delay_floor=update.feedback.delay_floor,
                delay_ceiling=update.feedback.delay_ceiling,
                silence_floor=update.feedback.silence_floor,
                silence_ceiling=update.feedback.silence_ceiling,
            ),
        )
        current_config = update
        LOGGER.info("configuration applied")

    adaptive.add_listener(apply)
    watcher_task: asyncio.Task | None = None
    if adaptive.path:
        watcher_task = asyncio.create_task(adaptive.watch())
    try:
        await observer.run()
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

