# NoStackTrace — plan

Hackathon: Build Your First AI App (Devpost, Yasir Insights). Submission deadline 2026-11-27, judging 2026-11-28 to 2026-12-06.
Goal: win.

Judging: implementation 30%, creativity 25%, usefulness 25%, presentation 20%.
Rules: disclose every AI tool used and what was your own work; never publish API keys.

## Pitch

"Software bugs give you a stack trace. Hardware bugs give you a dark LED."
An AI debugging assistant for beginner embedded labs (Arduino Uno + ESP32).

## Scope (locked)

- Input A: Wokwi project (`sketch.ino` + `diagram.json`) + symptom.
- Input B: code + typed pin table + symptom (real hardware on the lab bench).
- Output: ranked causes (code / wiring / power), a check to do for each, and a datasheet page citation.
- Deterministic checks in Python run first; Gemini handles the rest and explains.
- Pre-loaded datasheet facts for about 10 parts: LED + resistor, push button, potentiometer, DHT22, HC-SR04, LCD 16x2 I2C, servo SG90, MPU6050, buzzer, relay module.
- No PDF upload, no free chat, no voice, no STM32.
- Bilingual UI toggle (EN/VI). README and video in English with subtitles.

## Evaluation

- 20 broken Wokwi circuits with an answer key, written by a separate model (Codex) so the test set is independent of the prompt.
- Split: 10 dev (prompt tuning) and 10 test (held out, run once at the end).
- Baseline: the same circuits pasted into plain Gemini chat, compared with NoStackTrace.
- Every circuit is checked by hand in Wokwi.

## Story for the video

An illustrative scenario, stated as such ("Picture a second-year student..."), not a personal story:
an ESP32 maze robot with an HC-SR04 freezes for about 1 s and hits the wall in long corridors.
Cause: `pulseIn()` waits 1 s by default when no echo returns. Fix: pass a timeout, e.g. `pulseIn(ECHO, HIGH, 30000)`.

## Stack

Python + Gradio, Gemini free tier, Hugging Face Spaces with the key in Space Secrets.
Reliability during judging: cached results for the example circuits, a "Try an example" button, keep the Space awake.

## Open risks

- Hugging Face free CPU Basic Spaces: forum reports (late 2026) of a 403 cpu-basic quota and a PRO upgrade requirement. Create the Space early to confirm; keep a fallback host in mind.
- Gemini free-tier limits are not reliably published by third parties. Read the real limits on your project's page in Google AI Studio.
- Wokwi has no L298N, DC motor or IR line sensor; those can only be used through Input B.

## README must include

Problem, how AI is used, eval table (NoStackTrace vs plain chat), known limits, AI tools used and own contribution, setup steps.
