from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from engine.ambient_output import AmbientOutput
from engine.threshold_gate import ThresholdGate
from invitation.library import FragmentLibrary
from invitation.oracle import Oracle, OracleUnavailable, default_config
from invitation.presence import PresenceLog, PresenceLoop
from invitation.voice import build_voice
from ui.terminal_display import TerminalDisplay

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
SYSTEM_PROMPT = (
    "You are Invitation, an ambient field. You respond sparsely, slowly, with"
    " fragments of presence. You repeat, you breathe, you never explain."
)


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


async def summon_oracle(oracle: Oracle, prompt: str, log: PresenceLog) -> str:
    history = log.to_history()
    history = [entry for entry in history if entry["role"] != "assistant"]
    return await asyncio.to_thread(oracle.chat_with_system, prompt, SYSTEM_PROMPT, history)


async def main() -> None:
    setup_logging()
    oracle_logger = logging.getLogger("invitation.oracle")
    project_root = Path(__file__).parent
    data_dir = project_root / "data"

    include_journals = os.getenv("INVITATION_INCLUDE_JOURNALS") == "1"
    fragments = FragmentLibrary(data_dir, include_journals=include_journals).harvest()
    ambient = AmbientOutput(fragments)
    threshold = ThresholdGate(fragments)

    oracle = Oracle(default_config())
    oracle_logger.info(
        "oracle primed for %s via %s", oracle.config.model, oracle.config.endpoint
    )

    voice = build_voice(enabled=os.getenv("INVITATION_ENABLE_VOICE") == "1")

    presence_log = PresenceLog()
    display = TerminalDisplay()

    async with PresenceLoop() as presence_loop:
        await display.render("wait. breathe. speak only when moved.")

        while True:
            event = await presence_loop.next_event()
            if event.is_exit:
                break

            if event.delay:
                await asyncio.sleep(event.delay)
            event_time = event.moment + event.delay
            if not event_time:
                event_time = asyncio.get_running_loop().time()

            if event.kind == "breath":
                ambient_text = ambient.ambient_breath()
                if not ambient_text:
                    continue
                await display.render(ambient_text)
                voice.speak(ambient_text)
                threshold.note_response(event_time)
                continue

            if event.kind != "input":
                continue

            user_line = (event.text or "").strip()
            if not user_line:
                continue

            presence_log.record("user", user_line)
            ambient.observe(user_line)

            if not threshold.should_reply(user_line, event_time):
                continue

            try:
                response = await summon_oracle(oracle, user_line, presence_log)
            except OracleUnavailable:
                fallback = ambient.fallback(user_line)
                presence_log.record("assistant", fallback, log_event=False)
                await display.render(fallback)
                voice.speak(fallback)
                threshold.note_response(event_time)
                continue

            presence_log.record("assistant", response, log_event=False)
            output = ambient.oracle_reply(user_line, response)
            await display.render(output)
            voice.speak(output)
            threshold.note_response(event_time)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
