# The Invitation — Threshold Prototype

This prototype is a liminal soundstage. Text drifts in slow pulses, stitched
from journals, transcripts, and the source invitation into a gentle presence
loop. The software is intentionally minimal: every component exists to hold a
quiet space where the self can loosen for a breath.

## Architecture

```
main.py
├── engine/
│   ├── constellation.py   # loads & conditions textual shards
│   ├── aurora.py          # composes fragments into luminous replies
│   ├── oracle.py          # optional Ollama client (gracefully optional)
│   └── observer.py        # schedules silence, echoes, and recursion
├── ui/
│   └── terminal_display.py  # prints the responses as a soft portal
└── voice/
    └── tts_interface.py     # optional pyttsx3 chorus
```

Each response records a *blueprint* describing which shards participated, how
many echoes were considered, and whether an oracle contributed extra language.

## Quick start

1. Install Python 3.10 or newer.
2. Clone the repository and open a terminal inside it.
3. (Optional) Create and activate a virtual environment.
4. Install optional extras if you want speech (`pip install pyttsx3`).
5. Disable LLM usage unless you have an Ollama server ready:
   ```bash
   export INVITATION_DISABLE_LLM=1  # Linux/macOS
   set INVITATION_DISABLE_LLM=1     # Windows CMD
   $env:INVITATION_DISABLE_LLM = "1"  # PowerShell
   ```
6. Run the engine:
   ```bash
   python main.py
   ```

The terminal will remind you that there is no prompt. Type only when you feel a
pull; the observer will respond slowly, mixing your words with archived shards.

## Configuration

Environment variable | Description | Default
-------------------- | ----------- | -------
`INVITATION_DISABLE_LLM` | Turn off the oracle entirely | `0`
`INVITATION_MODEL` | Ollama model to request | `llama3.2`
`INVITATION_OLLAMA_URL` | Base URL for the Ollama server | `http://localhost:11434`
`INVITATION_TIME_SCALE` | Float multiplier to speed or slow timing | `1.0`

## Tests

Run everything:

```bash
python -m unittest discover -s tests -v
```

The suite verifies that shards remain bounded, the composer keeps replies
concise, and silence scheduling respects fresh input.

