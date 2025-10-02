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
5. If you don’t have Ollama running locally, disable the oracle:
   ```bash
   export INVITATION_DISABLE_LLM=1  # Linux/macOS
   set INVITATION_DISABLE_LLM=1     # Windows CMD
   $env:INVITATION_DISABLE_LLM = "1"  # PowerShell
   ```
6. (Optional) Edit `config/invitation.json` to tune pacing, layering, or
   architecture.
7. Run the engine:
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
`INVITATION_DISABLE_LLM` | Turn off the oracle entirely | `0`
`INVITATION_MODEL` | Ollama model to request | `llama3.2`
`INVITATION_OLLAMA_URL` | Base URL for the Ollama server | `http://localhost:11434`
`INVITATION_TIME_SCALE` | Float multiplier to speed or slow timing | `1.0`
`INVITATION_CONFIG` | Path to a custom config JSON file | `config/invitation.json`

Key sections inside `config/invitation.json`:

* `field` — controls clipping, slice counts, and mutation when harvesting shards.
* `weave` — defines the available architectures, oracle weighting, and the
  entangle/recursion biases for the composer.
* `pulse` — adjusts pacing, silence windows, and echo memory.
* `feedback` — sets the adaptive targets for response length and delay scaling.
* `metamorphosis` — governs how quickly the weave drifts between architectures.
* `monitor` — changes how often the configuration watcher checks for updates.

## Tests

Run everything:

```bash
python -m unittest discover -s tests -v
```

The suite verifies that shards remain bounded, the weave composes luminous but
finite replies, the observer cancels stale silences while triggering recursive
breaths, and the configuration layer applies live edits safely.
