"""Entry point for The Invitation ambient reflection engine."""
from __future__ import annotations

import asyncio
import logging
import os
import random
from pathlib import Path
from typing import Optional

from engine.ambient_output import AmbientOutputEngine
from engine.echo_logic import EchoChamber
from engine.local_llm import LocalLLM
from engine.presence_loop import PresenceConfig, PresenceLoop
from ui.terminal_display import TerminalDisplay
from voice.tts_interface import AmbientTTS


def _configure_logging() -> None:
    level_name = os.getenv("INVITATION_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def _build_presence_loop() -> PresenceLoop:
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"

    time_scale_env = os.getenv("INVITATION_TIME_SCALE", "1.0")
    try:
        time_scale = max(0.05, float(time_scale_env))
    except ValueError:
        time_scale = 1.0

    min_delay = 10.0 * time_scale
    max_delay = 90.0 * time_scale

    silence_min = 45.0 * time_scale
    silence_max = 180.0 * time_scale

    breath_min = 12.0 * time_scale
    breath_max = 24.0 * time_scale

    config = PresenceConfig(
        min_delay=min_delay,
        max_delay=max_delay,
        silence_range=(silence_min, silence_max),
        poll_interval=1.5 * time_scale,
        response_probability=0.45,
        breath_interval=(breath_min, breath_max),
    )

    echo = EchoChamber(max_items=72)

    model_name = os.getenv("INVITATION_MODEL", "llama3.2")
    enable_llm = os.getenv("INVITATION_DISABLE_LLM", "0") != "1"
    llm: Optional[LocalLLM]
    if enable_llm:
        llm = LocalLLM(model=model_name)
    else:
        llm = None

    composer = AmbientOutputEngine(
        data_dir=data_dir,
        echo_chamber=echo,
        llm=llm,
    )

    display = TerminalDisplay()
    tts_enabled = os.getenv("INVITATION_ENABLE_TTS", "0") == "1"
    tts = AmbientTTS(enabled=tts_enabled)

    seed_offset = os.getenv("INVITATION_RANDOM_SEED")
    if seed_offset:
        try:
            random.seed(int(seed_offset))
        except ValueError:
            random.seed(seed_offset)

    return PresenceLoop(
        composer=composer,
        echo=echo,
        display=display,
        tts=tts,
        config=config,
    )


async def main() -> None:
    _configure_logging()
    loop = await _build_presence_loop()
    await loop.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
