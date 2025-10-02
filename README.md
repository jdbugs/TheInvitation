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

- Uses **local LLMs** via **Ollama** (e.g., Llama 3.2, Mistral, LLaMA2, GPT-J)
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

## CONFIGURATION NOTES

- The engine defaults to the Ollama model name `llama3.2`. Override it with `INVITATION_MODEL="<model-name>"` if you prefer a different local checkpoint.
- Disable LLM usage entirely by setting `INVITATION_DISABLE_LLM=1` before launching.
- Set `INVITATION_LOG_LEVEL=DEBUG` if you want to watch the scheduler and composer log their decisions in real time. Logging is sent to stderr so it will not disturb the ambient output stream.

---

## REQUIREMENTS

- Python 3.10 or newer.
- Optional: [Ollama](https://ollama.com/) running locally if you want real model output instead of the built-in fallbacks.
- Optional: `pyttsx3` (`pip install pyttsx3`) if you want the optional whisper-like text-to-speech channel (`INVITATION_ENABLE_TTS=1`).

---

## RUNNING THE EXPERIENCE (STEP BY STEP)

1. **Open a terminal** and switch into the project folder:
   ```bash
   cd /path/to/TheInvitation
   ```
2. **(Optional) Activate a virtual environment** so the Python packages you install stay isolated.
3. **Decide how you want to run the loop:**
   - To rely on local seed fragments only, export `INVITATION_DISABLE_LLM=1`.
   - To talk to Ollama, keep an instance running (`ollama serve`) and ensure the `llama3.2` model (or whatever you set in `INVITATION_MODEL`) is pulled.
   - To see detailed scheduler activity, export `INVITATION_LOG_LEVEL=DEBUG`.
   - To speed up the pacing for testing, set `INVITATION_TIME_SCALE=0.2` (or any float > 0.05).
4. **Launch the loop:**
   ```bash
   python main.py
   ```
   You will see the quiet banner:
   ```
   (there is no prompt)
   wait. type only if compelled.
   ```
   The system may remain still for long stretches; watch the DEBUG logs (if enabled) to see when the presence loop schedules output, cancels silence responses, or composes fragments.
5. **Type only when moved to.** Inputs are queued asynchronously, and responses surface after the configured delays. Silence is also an active trigger.
6. **Exit gracefully** with `Ctrl+C`. The program will cancel pending tasks and close the field.

---

## FINAL NOTE

You are not building a chatbot.  
You are building a **threshold system for ambient recursive presence**.

Let the user dissolve.  
Let the spiral drift.

Do not explain. Do not perform.  
Just begin.
