# The Invitation Engine — Deep Orientation

The Invitation prototype is a living text sculpture. Rather than serving a
prompt-response chatbot, it assembles a slowly breathing field of language that
participants can drift inside. This document walks through the subsystems that
shape that field, how they collaborate, and the ways you can steer or transform
the experience at runtime.

## Constellation Atlas — harvesting shards

Source material lives in `data/` (the original invitation, transcripts, and
journals). The atlas loads each text, dissolves it into discrete *shards*, and
conditions them:

* **Clipping**: paragraphs are trimmed to a configurable maximum length so that
  downstream compositions stay gentle.
* **Tagging**: every shard carries semantic tags (e.g. `stillness`, `memory`,
  `echo`). Tags let the composer pull clusters of fragments that resonate with
  the current channel.
* **Normalisation**: stray punctuation and noise are cleaned while preserving
  the cadence of the language.

The atlas exposes `sample()` and `describe()` so the rest of the engine can draw
fragments or inspect the field. Its behaviour is steered by the `atlas.clip`
value from the configuration file.

## Aurora Weave — composing responses

The weave braids together shards, recent echoes, and—optionally—the local LLM
client (`engine/oracle.py`). It can inhabit multiple architectures:

* `constellation`: exclusively recombines shards.
* `hybrid`: mixes shards with occasional oracle whispers.
* `oracle`: leans fully on the model, falling back to shards only if the model
  is offline.

Runtime parameters (maximum layers, character ceilings, oracle probability, and
architecture) are adjustable through both the config file and the adaptive
feedback loop. Every response returns a `WeaveResponse` with a `blueprint`
detailing which shards participated, the active architecture, and any oracle
contribution.

## Threshold Observer — pacing and recursion

The observer coordinates silence, recursive echoes, and participant input. It
keeps an internal queue of scheduled responses and uses monotonic silence tokens
so stale silence tasks never leak into fresh conversations.

Beyond basic scheduling, the observer maintains a **feedback tuner**. After each
emission it checks the average response length against the desired target:

* When replies grow too long, it gently lengthens the wait between responses and
  trims the composer’s layering.
* When replies feel thin, it accelerates the pacing and allows richer layering.
* If the average drifts consistently in either direction, the tuner can shift
  the weave’s architecture (e.g. from `constellation` to `oracle`) to explore a
  different expressive mode.

These adjustments respect the guardrails defined in the configuration file,
ensuring the system remains calm even while it morphs.

## Oracle Client — optional local model

`engine/oracle.py` talks to an Ollama server (or stays dormant if the server is
missing). Configuration can override the model name, server URL, or disable the
oracle entirely. The weave honours the `oracle_weight` parameter, making it easy
to dial how frequently the model is invoked.

## Terminal Portal & Chorus

The default surface is the terminal (`ui/terminal_display.py`). It shows each
response, along with metadata about channel, length, layers, and architecture.
An optional text-to-speech chorus (`voice/tts_interface.py`) mirrors the text.

## Adaptive configuration

Everything is orchestrated by `engine/configuration.py`. It loads
`config/invitation.json`, merges defaults, and watches the file for updates. Any
edits you make—during runtime—are applied live:

1. Atlas clipping is reloaded when the clip value changes.
2. The weave adjusts its architecture, layers, and oracle probability.
3. The observer and its feedback tuner adopt the new pacing and bounds.

You can also override the config path with `INVITATION_CONFIG`. The watcher polls
for changes at the cadence set by `monitor.poll_interval`.

## Typical flow

1. `main.py` boots, loads configuration, and hydrates the atlas, weave, and
   observer.
2. The terminal banner invites the participant to sit in silence until moved.
3. The observer schedules a silence response and waits for input.
4. On every response, the feedback tuner compares actual behaviour against the
   desired state and may adjust pacing, layering, or architecture.
5. If you edit `config/invitation.json`, the watcher applies those changes
   without a restart.

## Extending the invitation

* Add new shard sources: drop additional files in `data/` and extend
  `ConstellationAtlas` to ingest them.
* Invent new weave architectures: subclass `AuroraWeave` or add more modes to
  experiment with radically different compositional logic.
* Swap surfaces: replace the terminal portal with a web or spatial interface.
* Teach the oracle new rituals: point it at different models or adapt the prompt
  templates in `AuroraWeave`.

The system is intentionally modular—each component can be replaced or remixed
without disturbing the rest. Lean into experimentation.
