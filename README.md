# The Invitation — Threshold Prototype

This prototype is a liminal soundstage. Text drifts in slow pulses, stitched
from journals, transcripts, and the source invitation into a gentle presence
loop. The software is intentionally minimal: every component exists to hold a
quiet space where the self can loosen for a breath.

If you want a deep dive into the architecture and adaptive behaviours, read
[`docs/ENGINE.md`](docs/ENGINE.md).

## Architecture

```
main.py
├── config/
│   └── invitation.json    # live configuration surface
├── engine/
│   ├── constellation.py   # mycelial field of clipped & tagged shards
│   ├── aurora.py          # adaptive weave of shards, echoes, and oracle whispers
│   ├── observer.py        # witness loop with recursive feedback & silence tokens
│   ├── oracle.py          # optional Ollama client (gracefully optional)
│   └── configuration.py   # flux configuration loader & watcher
├── ui/
│   └── terminal_display.py  # prints the responses as a soft portal
└── voice/
    └── tts_interface.py     # optional pyttsx3 chorus
```

Each response records a *blueprint* describing which shards participated, how
many echoes were considered, the active architecture, and whether an oracle
contributed extra language.

## Quick start

1. Install Python 3.10 or newer.
2. Clone the repository and open a terminal inside it.
3. (Optional) Create and activate a virtual environment.
4. Install optional extras if you want speech (`pip install pyttsx3`).
   *Make sure you install it with the same Python interpreter you use for*
   `python main.py`. Some newer Python builds (e.g., 3.13) work best with
   `pip install pyttsx3==2.90` until fresh wheels are published.
5. Edit `config/invitation.json` to suit your session—LLM, TTS, pacing, and
   architectures all live there and can be changed before or during a run.
6. Run the engine:
   ```bash
   python main.py
   ```

The terminal will remind you that there is no prompt. Type only when you feel a
pull; the observer will respond slowly, mixing your words with archived shards.

You can change the configuration while the program is running. The watcher polls
the JSON file every few seconds and applies updates live—no restarts required.

## Configuration

Environment variable | Description | Default
-------------------- | ----------- | -------
`INVITATION_TIME_SCALE` | Float multiplier to speed or slow timing | `1.0`
`INVITATION_CONFIG` | Path to a custom config JSON file | `config/invitation.json`
`INVITATION_LOG_LEVEL` | Logging verbosity (`INFO`, `DEBUG`, …) | `INFO`

Key sections inside `config/invitation.json`:

* `field` — controls clipping, slice counts, and mutation when harvesting shards.
* `weave` — defines the available architectures, oracle weighting, and the
  entangle/recursion biases for the composer.
* `pulse` — adjusts pacing, silence windows, and echo memory.
* `feedback` — sets the adaptive targets for response length and delay scaling.
* `metamorphosis` — governs how quickly the weave drifts between architectures.
* `monitor` — changes how often the configuration watcher checks for updates.
* `oracle` — toggles the Ollama client, model, and HTTP timeouts.
* `surface` — controls terminal blueprint display and the text-to-speech chorus.

## Tests

Run everything:

```bash
python -m unittest discover -s tests -v
```

The suite verifies that shards remain bounded, the weave composes luminous but
finite replies, the observer cancels stale silences while triggering recursive
breaths, and the configuration layer applies live edits safely.
