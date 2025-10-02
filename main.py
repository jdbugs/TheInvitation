"""Entry point for the Invitation prototype."""
from __future__ import annotations

from pathlib import Path
import asyncio
import logging
import os
import contextlib

from engine.aurora import AuroraWeave
from engine.constellation import MycelialConstellation
from engine.configuration import AdaptiveConfig, EngineConfig, resolve_config_path
from engine.observer import FeedbackTuning, PulseSettings, WitnessObserver
from engine.oracle import OracleClient
from ui.terminal_display import TerminalPortal
from voice.tts_interface import AmbientChorus

LOGGER = logging.getLogger("invitation.main")


def _configure_logging() -> None:
    level = os.environ.get("INVITATION_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _scaled(settings: PulseSettings) -> PulseSettings:
    scale = float(os.environ.get("INVITATION_TIME_SCALE", "1.0"))
    if scale <= 0:
        return settings
    return PulseSettings(
        min_delay=settings.min_delay * scale,
        max_delay=settings.max_delay * scale,
        min_silence=settings.min_silence * scale,
        max_silence=settings.max_silence * scale,
        echo_memory=settings.echo_memory,
    )


def _build_oracle(config: EngineConfig) -> OracleClient:
    return OracleClient.from_config(config.oracle)


def _build_chorus(config: EngineConfig) -> AmbientChorus | None:
    chorus_cfg = config.surface.chorus
    if not chorus_cfg.enabled:
        return None
    chorus = AmbientChorus(
        enabled=chorus_cfg.enabled,
        voice=chorus_cfg.voice,
        rate=chorus_cfg.rate,
        volume=chorus_cfg.volume,
    )
    return chorus if chorus.enabled else chorus


async def main() -> None:
    _configure_logging()
    base = Path(__file__).parent
    config_path = resolve_config_path(base)
    adaptive = AdaptiveConfig(config_path)
    snapshot = adaptive.snapshot()

    constellation = MycelialConstellation.from_data_dir(base / "data", snapshot.field)
    oracle = _build_oracle(snapshot)
    weave = AuroraWeave(
        constellation,
        config=snapshot.weave,
        metamorphosis=snapshot.metamorphosis,
        oracle=oracle,
    )
    chorus = _build_chorus(snapshot)
    display = TerminalPortal(
        show_blueprint=snapshot.surface.show_blueprint,
        chorus=chorus,
    )
    observer = WitnessObserver(
        weave,
        display,
        settings=_scaled(
            PulseSettings(
                min_delay=snapshot.pulse.min_delay,
                max_delay=snapshot.pulse.max_delay,
                min_silence=snapshot.pulse.min_silence,
                max_silence=snapshot.pulse.max_silence,
                echo_memory=snapshot.pulse.echo_memory,
            )
        ),
        tuning=FeedbackTuning(
            target_chars=snapshot.feedback.target_chars,
            tolerance=snapshot.feedback.tolerance,
            learning_rate=snapshot.feedback.learning_rate,
            architecture_push=snapshot.feedback.architecture_push,
            max_layers_ceiling=snapshot.feedback.max_layers_ceiling,
            min_layers_floor=snapshot.feedback.min_layers_floor,
            delay_floor=snapshot.feedback.delay_floor,
            delay_ceiling=snapshot.feedback.delay_ceiling,
            silence_floor=snapshot.feedback.silence_floor,
            silence_ceiling=snapshot.feedback.silence_ceiling,
        ),
    )

    current_config = snapshot
    current_oracle = oracle

    def apply(update: EngineConfig) -> None:
        nonlocal constellation, current_config, current_oracle
        if update.field != current_config.field:
            constellation = MycelialConstellation.from_data_dir(base / "data", update.field)
            weave.set_constellation(constellation)
        weave.reconfigure(weave=update.weave, metamorphosis=update.metamorphosis)
        observer.apply_config(
            settings=_scaled(
                PulseSettings(
                    min_delay=update.pulse.min_delay,
                    max_delay=update.pulse.max_delay,
                    min_silence=update.pulse.min_silence,
                    max_silence=update.pulse.max_silence,
                    echo_memory=update.pulse.echo_memory,
                )
            ),
            tuning=FeedbackTuning(
                target_chars=update.feedback.target_chars,
                tolerance=update.feedback.tolerance,
                learning_rate=update.feedback.learning_rate,
                architecture_push=update.feedback.architecture_push,
                max_layers_ceiling=update.feedback.max_layers_ceiling,
                min_layers_floor=update.feedback.min_layers_floor,
                delay_floor=update.feedback.delay_floor,
                delay_ceiling=update.feedback.delay_ceiling,
                silence_floor=update.feedback.silence_floor,
                silence_ceiling=update.feedback.silence_ceiling,
            ),
        )
        if update.oracle != current_config.oracle:
            current_oracle = _build_oracle(update)
            weave.set_oracle(current_oracle, response_timeout=update.oracle.response_timeout)
        if update.surface != current_config.surface:
            chorus = _build_chorus(update)
            display.apply_surface(
                show_blueprint=update.surface.show_blueprint,
                chorus=chorus,
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
