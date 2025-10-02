# The Invitation Engine — Deep Orientation

The Invitation prototype is a living text sculpture. Rather than serving a
prompt-response chatbot, it assembles a slowly breathing field of language that
participants can drift inside. This document walks through the subsystems that
shape that field, how they collaborate, and the ways you can steer or transform
the experience at runtime.

## Mycelial Constellation — harvesting shards

Source material lives in `data/` (the original invitation, transcripts, and
journals). The constellation loads each text, dissolves it into discrete *shards*,
and conditions them:

* **Clipping**: paragraphs are trimmed to a configurable maximum length so that
  downstream compositions stay gentle.
* **Tagging**: every shard carries semantic tags (e.g. `stillness`, `memory`,
  `echo`). Tags let the composer pull clusters of fragments that resonate with
  the current channel.
* **Mutation**: a configurable mutation rate swaps tags from the base palette to
  keep the field in slow motion, subtly shifting which shards appear together.

The constellation exposes `sample()` and `describe()` so the rest of the engine
can draw fragments or inspect the field. Its behaviour is steered by the
`field.*` values from the configuration file.

## Aurora Weave — composing responses

The weave braids together shards, recent echoes, and—optionally—the local LLM
client (`engine/oracle.py`). It inhabits a set of named architectures defined in
`config/invitation.json`:

* Each architecture specifies how many shards to layer, how strongly to favour
  the oracle, and whether to echo the participant’s last utterance.
* The weave tracks a *metamorphosis window*. Drift in response length or the
  configured chaos/reactivity values can nudge the active architecture forward or
  backward through the cascade.
* Every response returns a `WeaveResponse` with a blueprint detailing which
  shards participated, the active architecture, and any oracle contribution.

`AuroraWeave.metabolise()` is called after each emission so the weave can adjust
its oracle weighting and potentially advance to a new architecture based on the
feedback loop.

## Witness Observer — pacing and recursion

The observer coordinates silence, recursive echoes, and participant input. It
keeps an internal queue of scheduled responses and uses monotonic silence tokens
so stale silence tasks never leak into fresh conversations.

Beyond basic scheduling, the observer maintains a **feedback tuner**. After each
emission it checks the average response length against the desired target:

* When replies grow too long, it gently lengthens the wait between responses and
  allows the weave to metabolise toward architectures with fewer shards.
* When replies feel thin, it accelerates the pacing and invites richer layering.
* If the average drifts consistently in either direction, the tuner nudges the
  weave, which may migrate to a different architecture or adjust its oracle
  weighting.

Silence responses are scheduled with a unique token; new participant input
cancels the pending task so silence never speaks over a fresh offering.

## Oracle Client — optional local model

`engine/oracle.py` talks to an Ollama server (or stays dormant if the server is
missing). The `oracle.*` section of `config/invitation.json` toggles the client,
chooses the model, and sets HTTP timeouts. The weave honours the
`oracle_weight` parameter, making it easy to dial how frequently the model is
invoked.

## Terminal Portal & Chorus

The default surface is the terminal (`ui/terminal_display.py`). It shows each
response, along with metadata about channel, length, layers, and architecture.
The `surface.*` section controls whether that blueprint line appears and whether
the text-to-speech chorus (`voice/tts_interface.py`) should speak alongside the
text. Chorus voice, rate, and volume can be tuned live. Install `pyttsx3` inside
the same interpreter that launches `main.py`; on Python 3.13 you may need to pin
`pyttsx3==2.90` until newer wheels arrive.

## Adaptive configuration

Everything is orchestrated by `engine/configuration.py`. It loads
`config/invitation.json`, merges defaults, and watches the file for updates. Any
edits you make—during runtime—are applied live:

1. The constellation rehydrates if clipping or mutation settings change.
2. The weave adjusts its architecture cascade, oracle weighting, and biases.
3. The observer and its feedback tuner adopt the new pacing and guardrails.
4. The oracle client and terminal surface refresh whenever `oracle.*` or
   `surface.*` change.

You can also override the config path with `INVITATION_CONFIG`. The watcher polls
for changes at the cadence set by `monitor.poll_interval`.

## Typical flow

1. `main.py` boots, loads configuration, and hydrates the constellation, weave,
   and observer.
2. The terminal banner invites the participant to sit in silence until moved.
3. The observer schedules a silence response and waits for input.
4. On every response, the feedback tuner compares actual behaviour against the
   desired state and may adjust pacing, layering, or architecture.
5. If you edit `config/invitation.json`, the watcher applies those changes
   without a restart.

## Extending the invitation

* Add new shard sources: drop additional files in `data/` and extend the base
  tags or mutation behaviour in `field.*`.
* Invent new weave architectures: add more entries under `weave.architectures`
  to experiment with radically different compositional logic.
* Swap surfaces: replace the terminal portal with a web or spatial interface.
* Teach the oracle new rituals: point it at different models or adapt the prompt
  templates in `AuroraWeave`.

The system is intentionally modular—each component can be replaced or remixed
without disturbing the rest. Lean into experimentation.
