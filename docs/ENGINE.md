# Engine notes

The current build is intentionally simple. Rather than a sprawling ritual stack,
there are three small collaborators: the seed library, the response composer, and
the presence loop. This document explains how they work together and how the
configuration file steers them.

## 1. Configuration loader (`engine/configuration.py`)

* `parse_config` reads `config/invitation.json` (or the path set by
  `INVITATION_CONFIG`) and produces frozen dataclasses.
* `AdaptiveConfig` stores the current config, exposes `snapshot()`, and, when a
  path exists, polls the file every `monitor.poll_interval` seconds. When the
  file changes, it reloads the JSON and notifies listeners.
* Each section has sensible defaults so the program still runs if the JSON is
  missing or only partially filled in.

## 2. Seed library (`engine/library.py`)

* Walks the `data/` directory, reading `.txt` and `.md` files.
* Splits files on blank lines, strips whitespace, drops fragments shorter than
  `library.min_words`, and clips each fragment to `library.clip_chars`.
* Keeps track of the originating filename so the terminal can optionally show
  where a fragment came from.
* Exposes `pick(count, *, avoid=None)` which returns up to
  `library.max_fragments` random snippets, preferring fragments that are not in
  the optional `avoid` set of recently used text.

## 3. Response composer (`engine/composer.py`)

* When asked to `craft`, it samples fragments from the library and optionally
  calls the oracle.
* The oracle prompt is short and specific: “two sentences, kind, steady, clear”.
  If Ollama is offline or times out, the composer simply ignores the oracle and
  uses library fragments alone.
* Replies begin with optional intro lines: a silence marker, an echo of what the
  listener typed, and an acknowledgement phrase chosen from the configured
  variants (the placeholders `{input}` and `{channel}` are substituted when
  present). Duplicate fragments are collapsed, the composer avoids recently used
  snippets, and each reply ends with a rotating closing line. Everything is
  separated by blank lines for legibility and clipped to `response.max_chars`.
* `reconfigure` lets the running program swap in a fresh library, config, or
  oracle instance when the JSON file changes.

## 4. Presence loop (`engine/presence.py`)

* Prints the banner, reads `stdin` on a background executor, and queues input.
* Remembers the lengths of the last few responses and uses that history to nudge
  the next silence delay toward the `feedback.target_chars` window.
* Maintains a monotonic silence token: whenever new input arrives, the loop
  cancels the pending silence task and increments the token so no stale response
  can fire later.
* Calls the composer for user-triggered replies immediately, then schedules a
  new silence response at a random time between `timing.min_silence` and
  `timing.max_silence` (adjusted by the feedback window).

## 5. Terminal surface (`ui/terminal_display.py`)

* Prints the configured prefix (default: “— invitation —”) followed by the
  response text.
* Optional debug mode adds a line that shows the channel (`input` or `silence`),
  the number of characters, whether the oracle contributed, and every fragment
  with its source filename.
* If the `voice` section keeps the chorus enabled and `pyttsx3` is installed in
  the same Python interpreter, the surface asks it to speak the response.

## 6. Main script (`main.py`)

1. Load the configuration and build the initial library, oracle, composer,
   portal, and presence loop.
2. Register a listener so that when the JSON file changes it can rebuild the
   library (if needed), refresh the oracle, reconfigure the composer, update the
   portal, and adjust the loop timing.
3. Start the optional watcher task and then call `PresenceLoop.run()`.

The result is a compact, easily inspectable system that you can tweak by editing
one JSON file or by swapping out text files under `data/`.
