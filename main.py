"""Entry point for the Invitation prototype."""
from __future__ import annotations

from pathlib import Path
import asyncio
import logging
import os

from engine.aurora import AuroraWeave
from engine.constellation import ConstellationAtlas
from engine.observer import ObserverSettings, ThresholdObserver
from engine.oracle import OracleClient
from ui.terminal_display import TerminalPortal


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
    atlas = ConstellationAtlas.from_data_dir(base / "data")
    oracle = OracleClient.from_env()
    weave = AuroraWeave(atlas, oracle=oracle)
    display = TerminalPortal()
    observer = ThresholdObserver(weave, display, settings=_time_scaled(ObserverSettings()))
    await observer.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

