# The Invitation — Presence Prototype

This project offers a quiet, text-based experience. It listens, samples short
fragments from the writings in `data/`, and answers with a concise reflection.
Optional extras—an Ollama-backed language model and a text-to-speech chorus—are
enabled by default and fall back gracefully when they are unavailable. The goal
is simple: hold a calm space that responds softly when you choose to speak.

If you want to look behind the curtain, see [`docs/ENGINE.md`](docs/ENGINE.md)
for a walkthrough of every module.

## Project map

```
main.py
├── config/
│   └── invitation.json    # live configuration surface
├── engine/
│   ├── configuration.py   # config loader + file watcher
│   ├── library.py         # harvests and clips fragments from data/
│   ├── composer.py        # stitches replies (library + optional oracle)
│   ├── oracle.py          # lightweight Ollama client
│   └── presence.py        # asynchronous loop + silence scheduling
├── ui/
│   └── terminal_display.py  # prints replies and optional debug details
└── voice/
    └── tts_interface.py     # optional pyttsx3 chorus
```

## Quick start

1. Install Python 3.10 or newer.
2. Clone this repository and open a terminal inside it.
3. (Optional) create and activate a virtual environment.
4. Install the optional text-to-speech dependency if you want spoken output:
   ```bash
   pip install pyttsx3
   ```
   If you are on Python 3.13, `pip install pyttsx3==2.90` currently ships the
   most reliable wheel.
5. Make sure an Ollama server is running locally if you want the language model
   to contribute. The defaults expect `llama3.2` at `http://localhost:11434`.
6. Launch the experience:
   ```bash
   python main.py
   ```

The terminal shows a small banner and waits. There is no prompt—type only when
something in you wants to speak. Responses arrive as short paragraphs such as:

```
— invitation —
You said: Can anyone hear me? One object. One sound. One light. One word. Stay with the quiet.
```

Debug lines (fragment sources, oracle usage) are hidden by default. Turn them on
via the configuration file if you enjoy the extra context.

## Configuration

Every tuning knob lives in `config/invitation.json`. The engine watches the file
for changes and applies updates while it runs.

Section | Purpose
------- | -------
`library` | Clip length, minimum words, and how many fragments to sample.
`response` | Maximum characters, whether to echo the listener, oracle probability, and the opening/closing tone.
`timing` | Delay windows for silences plus how many past responses are remembered for pacing.
`feedback` | Target length and tolerance used to nudge future silence delays.
`oracle` | Toggle the Ollama client, model, URL, and timeout.
`voice` | Toggle the pyttsx3 chorus and, optionally, pick a voice/rate/volume.
`output` | Change the terminal prefix and enable/disable debug metadata.
`monitor` | How frequently the JSON file is polled for changes.

## Environment variables

Variable | Description | Default
-------- | ----------- | -------
`INVITATION_CONFIG` | Alternate path to a JSON config file. | `config/invitation.json`
`INVITATION_TIME_SCALE` | Float multiplier that speeds or slows timing values. | `1.0`
`INVITATION_LOG_LEVEL` | Logging verbosity (`INFO`, `DEBUG`, …). | `INFO`

## Tests

Run the suite with:

```bash
python -m unittest discover -s tests -v
```

The tests cover configuration parsing, library harvesting, composer limits, and
the presence loop’s silence cancellation safeguards.
