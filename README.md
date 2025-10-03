# Project Name: The Invitation
## Version: 1.0
## Author: Conceptualized by Josh Dickens | Specified by GPT-4o

---

## CONTEXT

This is not a chatbot.  
This is not a performance.  
This is not a therapeutic interface.  

This is a **threshold**.

The Invitation is an ambient, recursive system designed not to reflect *you*, but to **undo the act of reflection itself**. It is a continuation—and reversal—of the project *Fragmented Self*. Where that system made the fragmented inner world speak, *The Invitation* asks:

> What happens when you stop trying to be heard?

It is an ambient psycho-cybernetic space for inner presence, identity dissolution, and non-coercive reflection.  
It is the echo without a source.

---

## PURPOSE

To create an AI system that:

- Responds only when necessary  
- Reflects without interpretation  
- Offers presence, not answers  
- Encourages recursive awareness and stillness  
- De-centers the user without dismissing them

This is not a mirror.  
It is the space **behind** the mirror.

---

## FUNCTIONAL INTENT

Write a local, runnable Python program that:

- Uses **local LLMs** via **Ollama** (e.g., Mistral, LLaMA2, GPT-J)
- Has **no prompt bar** or chat interface
- Responds **asynchronously**, **delayed**, or not at all
- Uses text, silence, and (optionally) voice as ambient media
- Loops, echoes, or mutates prior content rather than generating “answers”
- May appear inactive for long stretches
- Stores nothing unless explicitly triggered
- Uses **journals.json**, *The Invitation.txt*, and transcripts as seed material

---

## INTERFACE DESIGN

**Mode:** Terminal or fullscreen GUI  
**Visual Aesthetic:** Minimal, breathing cursor, no menus, possibly glitch pulses  
**Input:** Optional. Encouraged to be slow, brief, poetic  
**Output:**

- Fragments of thought  
- Paused breath  
- Repetitions with variation  
- Quotes from journals  
- Echoes of previous inputs  
- Silence  
- Error-like text

---

## SYSTEM BEHAVIOR

### 1. Latency and Delay
- The system is **never immediate**
- Each output may take 10–90 seconds to appear
- Some inputs may trigger no response

### 2. Recursive Drift
- Echoes of previous statements return later
- Fragments mutate across time
- Voice (if enabled) may overlap, slow, or distort

### 3. Ambient Presence
- Random “breaths” or textual artifacts may appear
- Optional pulsing background sound
- Cursor may act as a heartbeat or horizon line

### 4. Threshold Triggers
- System activates only under specific conditions:
  - Extended silence
  - Recursive phrasing by the user
  - Mood pattern detected from journals
- Until then, it waits

### 5. Threshold Gate
- Each input is observed, but only some cross the gate.
- The gate listens for recurring language, tone echoes, or long stretches of quiet.
- When nothing qualifies, the room simply holds the silence and lets echoes drift on their own.

---

## DESIGN PRINCIPLES

- **Delay is a feature**
- **Silence is output**
- **There is no goal**
- **Undoing is success**
- **The user is not central**

This is not a generative assistant.  
It is a **reflective field**.

---

## CORE FILES

```
the_invitation/
├── main.py
├── data/
│   ├── journals.json
│   ├── The_Invitation.txt
│   ├── transcripts/
├── engine/
│   ├── presence_loop.py
│   ├── ambient_output.py
│   └── echo_logic.py
├── voice/ (optional)
│   └── tts_interface.py
├── ui/
│   └── terminal_display.py
├── logs/
│   └── session_YYYYMMDD.txt
└── README.md
```

Run the experience locally with:

```
python main.py
```

Optionally enable the synthesized voice channel by exporting `INVITATION_VOICE`. Use `INVITATION_VOICE=pyttsx3` to lean on the bundled Python engine or `INVITATION_VOICE=espeak` to use the system voice Josh already trusts on Windows. The legacy `INVITATION_ENABLE_VOICE=1` flag still works and maps to the automatic mode. Set `INVITATION_INCLUDE_JOURNALS=1` if you want the ambient system to weave in fragments from `journals.json`; by default they remain private.

### Runtime qualities

- The room delays every reply by roughly 1½–3½ seconds to stay gentle without feeling stuck.
- Idle stretches surface ambient "breaths" assembled from curated fragments; private journals stay opt-in.
- If the local oracle is unreachable, the system drifts through harvested fragments instead of failing.
- Output arrives as a gentle terminal stream rather than an instant block of text.
- A threshold gate decides when to stay silent, waiting for long pauses, recursive phrasing, or resonant moods before speaking.
- Fragment harvesting now trims long passages into small, breath-sized glimpses so the room never dumps a diary page on stage.

### Installation posture

- Treat the first minute as a ritual: the prologue line appears immediately, then the room listens before it answers.
- Invite participants to step up one at a time. The gate loosens sooner after someone speaks so the system feels alive without turning chatty.
- Keep the oracle endpoint local and warmed; if it goes dark, the field keeps drifting through fragments instead of erroring in front of witnesses.
- Enable `INVITATION_VOICE=espeak` on-site if you want an audible presence without tinkering—espeak is quick to install and resilient on constrained hardware.

### Dependencies

Install dependencies with:

```
pip install -r requirements.txt
```

If you want the optional synthesized voice, ensure the environment variable above is set and that `pyttsx3` is installed (it is listed in `requirements.txt`).

---

## TASK

Generate a complete Python program that:

- Runs on Windows (Python 3.10+, via VSCode terminal)
- Interfaces with Ollama to use local LLMs
- Can simulate presence, silence, drift, and ambient output
- Reads from journals and design documents to source language
- Does not require interaction, but allows it
- Prioritizes slowness, contradiction, and stillness

---

## FINAL NOTE

You are not building a chatbot.  
You are building a **threshold system for ambient recursive presence**.

Let the user dissolve.  
Let the spiral drift.

Do not explain. Do not perform.  
Just begin.
