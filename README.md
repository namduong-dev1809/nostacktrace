---
title: NoStackTrace
emoji: 🔌
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 6.32.0
app_file: app.py
pinned: false
short_description: Runtime-traced AI debugging for Arduino Uno and ESP32 labs
---

# NoStackTrace

**Software bugs give you a stack trace. Hardware bugs give you a dark LED.**

NoStackTrace helps beginner embedded students debug Arduino Uno and ESP32 lab projects.
It does not only read your code: it adds a trace to your sketch, you run it (in Wokwi or on the
real board), and the diagnosis is grounded in what actually happened at runtime.

## The problem

In a first-year embedded lab, the program compiles, the board powers on, and nothing works.
There is no error message. A chat assistant can only guess from the code, and the guess that
sounds most plausible is not always the one that happened.

## How it works

1. **Code checks (no AI).** Python rules parse `sketch.ino` and Wokwi `diagram.json` and flag
   facts: input-only ESP32 pins used as outputs, unwired pins, floating buttons, an LED without a
   resistor, `pulseIn()` without a timeout, DHT read too often, ADC2 used with Wi-Fi, I2C address
   mismatch.
2. **Trace it (no AI).** One click makes a traced copy of the sketch. Macros wrap
   `digitalRead/digitalWrite/analogRead/pinMode/pulseIn` and record the source line, pin, value and
   duration, scan the I2C bus at startup and report the slowest `loop()` pass. Line numbers match
   the student's original code. Events are buffered and printed between `loop()` passes, so the
   trace does not add delay inside timing-sensitive code.
3. **Runtime checks (no AI).** The pasted Serial log is parsed: a `pulseIn()` that blocked for 1 s,
   a slow `loop()`, no I2C device or the wrong address, `setup()` that never finished.
4. **AI diagnosis.** Gemini (Groq as fallback) gets the code, wiring, confirmed findings, the
   runtime trace and a short list of verified datasheet facts. It returns up to 4 ranked causes,
   each with a 2-minute check, a fix and its source. Every card says where the claim comes from:
   *Seen in runtime trace*, *Verified by code check*, *Datasheet · part p.N*, or *AI reasoning*.

### Example: the maze robot (illustrative scenario)

Picture a second-year student whose ESP32 maze robot freezes and then drives into the wall in long
corridors. The real trace from Wokwi (ECHO wire removed so no echo returns) shows it directly:

```text
NST|t=706|L16|digitalWrite(5,0)
NST|t=1706|L17|pulseIn(18)=0|took_us=1000018
NST|t=4038|loop_slowest_us=3450498|loops=1
```

`pulseIn()` on line 17 waits its default 1 s when no echo returns. Fix:
`pulseIn(ECHO, HIGH, 30000)`. This log is in `examples/maze-sonar/serial_log.txt`, unedited.

The trace also caught a bug in itself during development: an earlier version printed inside
`digitalWrite()`, and that ~1 ms of Serial output made `pulseIn()` miss the echo. Now events are
buffered (see `tests/test_trace.py`).

## Evaluation

20 broken circuits (10 dev, 10 held-out test) were written by a separate model (Codex) from an
answer key, without seeing this app's rules or prompts. Both arms get the same sketch,
`diagram.json` and symptom and use the same Gemini model; a Gemini judge compares each answer with
the key (`run_eval.py`).

| Split | NoStackTrace top-1 | Plain Gemini top-1 |
| --- | --- | --- |
| Dev (10), code + wiring only, no trace | 10/10 | 10/10 |
| Test (10) | not run yet | not run yet |

Honest reading: on static code + wiring, a plain chat model already finds these faults. Answers
from NoStackTrace were shorter (median 66 vs 207 words) and cite their source, but that alone is
not a reason to use a new app. The difference Trace mode adds is evidence from the running board,
which a chat model reading code does not have. That claim is shown by the maze example, not yet
measured on the eval set.

All 20 eval sketches and the example compile with `arduino-cli`, both original and traced
(`compile_check.py`). The eval circuits have not all been run by hand in Wokwi.

## Known limits

- Arduino Uno and ESP32 only; about 10 common parts have datasheet facts.
- The trace buffer holds 24 events per `loop()` pass (about 480 bytes of RAM on the Uno).
  If `setup()` blocks forever, the buffered events before it are not printed.
- The sketch's own `Serial.print` lines appear before the trace events of the same pass.
- Free API tiers: Gemini allows about 20 requests per day per model, so the app tries several
  models and then Groq. Example results are cached in `cache/`.
- AI can be wrong. Cards labelled *AI reasoning* are guesses to check, not facts.

## AI tools used, and my own work

- **Claude Code (Claude Opus)**: wrote most of the Python code (checks, trace generator, Gradio UI,
  eval scripts) under my direction, and reviewed the plan with me.
- **Codex (OpenAI)**: wrote the 20 eval circuits and answer key, separately from the app.
- **Gemini API / Groq API**: the AI inside the app and the eval judge.
- **My own work**: <!-- TODO (author): describe in your own words before submitting -->
  chose the problem from my own embedded-systems lab experience, made the scope and design
  decisions, ran the traced sketches in Wokwi and recorded the real Serial logs.

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Create `.env` with `GEMINI_API_KEY=...` (optional: `GROQ_API_KEY=...`), then:

```bash
.venv/bin/python app.py
```

On Hugging Face Spaces, set `GEMINI_API_KEY` and `GROQ_API_KEY` as Space secrets. Never commit
keys.

Tests: `python -m unittest discover -s tests`.
