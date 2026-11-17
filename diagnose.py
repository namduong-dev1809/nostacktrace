"""Code checks first, then Gemini explains and covers what the rules cannot see."""
import json
import logging
import os
from pathlib import Path

import httpx
from google import genai
from google.genai import errors, types

from checks import Diagram, run_checks
from nst_trace import check_trace, parse_log, summarize

ROOT = Path(__file__).parent
# Tried in order; a busy (503), rate-limited (429) or timed-out model falls through to the next one.
# Gemini first (best answers, ~20 requests/day/model on the free tier), then Groq (~1000/day, 8k tokens/min).
MODELS = os.environ.get("GEMINI_MODELS", "gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",")
if os.environ.get("GROQ_API_KEY"):
    MODELS += ["groq:openai/gpt-oss-120b", "groq:qwen/qwen3.8-27b"]
MODEL = MODELS[0]
DATASHEETS = json.loads((ROOT / "datasheets.json").read_text()) if (ROOT / "datasheets.json").exists() else {}

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "causes": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "category": {"type": "string", "enum": ["code", "wiring", "power", "timing", "part-specific"]},
                "likelihood": {"type": "string", "enum": ["high", "medium", "low"]},
                "why": {"type": "string"},
                "check": {"type": "string"},
                "fix": {"type": "string"},
                "source": {"type": "string"},
            },
            "required": ["title", "category", "likelihood", "why", "check", "fix", "source"],
        }},
    },
    "required": ["summary", "causes"],
}

SYSTEM = """You help beginner students debug Arduino Uno / ESP32 lab circuits.
Rank the most likely root causes of the symptom, most likely first, at most 4.
Rules:
- "Confirmed findings" come from deterministic code checks and from the runtime trace. Treat them as facts and include each one that can explain the symptom.
- A "Runtime trace" shows what really happened when the student ran the sketch (NST lines: source line, call, value, duration). It outranks guesses from reading the code: quote the trace line you rely on in "why", and drop causes the trace rules out.
- Only cite a datasheet fact from the "Datasheet facts" list, by its key, as source "datasheet:<key>". Never invent page numbers or specs.
- source is "rule:<id>" for a confirmed finding, "datasheet:<key>" for a listed fact, or "reasoning" otherwise.
- When a runtime trace finding (id starting with "trace-") and a code check describe the same cause, merge them into one cause with source "rule:<trace id>": what really happened beats what the code suggests.
- "check" is one concrete thing the student can do in under 2 minutes to confirm the cause.
- Quote the exact line or pin from the student's code or wiring in "why".
- If nothing explains the symptom, say so in summary instead of guessing.
Answer in {lang}."""


_CLIENT = None


def _client():
    # Keep one client alive: a garbage-collected client closes its HTTP session mid-request.
    global _CLIENT
    # 25 s per call and no SDK retries: on a busy model we move to the next one instead of backing off.
    _CLIENT = _CLIENT or genai.Client(http_options=types.HttpOptions(  # reads GEMINI_API_KEY from env
        timeout=25_000, retry_options=types.HttpRetryOptions(attempts=1)))
    return _CLIENT


def build_prompt(sketch, diagram, pin_table, symptom, serial_log=""):
    findings, parts = [], ""
    if diagram.strip():
        findings = run_checks(sketch, diagram)
        dg = Diagram(diagram)
        parts = f"Board: {dg.board}\nWiring nets:\n{dg.summary()}"
    else:
        parts = f"Pin table typed by the student (real hardware):\n{pin_table}"
    facts = "\n".join(f"- {k}: {v['fact']} ({v['source']}, {'p.' + str(v['page']) if v.get('page') else v['url']})"
                      for k, v in DATASHEETS.items() if not k.startswith("_")) or "(none)"
    trace = ""
    if serial_log.strip():
        events = parse_log(serial_log)
        findings += check_trace(events, sketch)
        own = [l[:300] for l in serial_log.splitlines() if l.strip() and "NST|" not in l][-20:]
        trace = (f"\n\nRuntime trace ({len(events)} NST events; line numbers match the code above):\n{summarize(events)}"
                 + ("\n\nThe sketch's own Serial output (last lines):\n" + "\n".join(own) if own else ""))
    prompt = f"""Symptom: {symptom}

{parts}

Code:
```cpp
{sketch}
```

Confirmed findings:
{json.dumps(findings, indent=1) if findings else "(none)"}

Datasheet facts:
{facts}{trace}"""
    return prompt, findings


class Retryable(Exception):
    pass


def generate(model, prompt, system=None, schema=None):
    """One call to one model; returns text. Raises Retryable when the next model should be tried."""
    if model.startswith("groq:"):
        body = {"model": model[5:], "temperature": 0.2,
                "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]}
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}}
        try:
            r = httpx.post("https://api.groq.com/openai/v1/chat/completions", json=body, timeout=40,
                           headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"})
        except httpx.TimeoutException as e:
            raise Retryable(e)
        if r.status_code == 429 or r.status_code >= 500:
            raise Retryable(f"groq {r.status_code}")
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    config = types.GenerateContentConfig(temperature=0.2, system_instruction=system, **(
        {"response_mime_type": "application/json", "response_schema": schema} if schema else {}))
    try:
        return _client().models.generate_content(model=model, contents=prompt, config=config).text
    except (errors.ServerError, errors.ClientError) as e:
        if getattr(e, "code", None) in (429, 503, 504, 404):
            raise Retryable(e)
        raise
    except httpx.TimeoutException as e:
        raise Retryable(e)


def generate_any(prompt, system=None, schema=None, models=None, parse=None):
    """Try models in order; returns (text or parse(text), model).
    Any failure (quota, bad key, 4xx, network, malformed answer) moves on to the next model;
    when all fail, the error names each model's failure."""
    errors = []
    for model in models or MODELS:
        try:
            text = generate(model, prompt, system, schema)
            return (parse(text) if parse else text), model
        except Exception as e:  # noqa: BLE001 - every failure is logged and the next model is tried
            logging.warning("model %s failed: %s: %s", model, type(e).__name__, str(e)[:200])
            errors.append(f"{model}: {type(e).__name__}")
    raise RuntimeError("all models failed (" + "; ".join(errors) + ")")


LIKELIHOOD = {"high", "medium", "low"}


def parse_result(text):
    """Model JSON -> result dict with every field render() needs; raises ValueError otherwise."""
    r = json.loads(text or "")
    if not isinstance(r, dict) or not isinstance(r.get("summary"), str) or not isinstance(r.get("causes"), list):
        raise ValueError("answer is missing summary/causes")
    for c in r["causes"]:
        if not isinstance(c, dict) or not all(isinstance(c.get(k), str) for k in SCHEMA["properties"]["causes"]["items"]["required"]):
            raise ValueError("a cause is missing a field")
        if c["likelihood"] not in LIKELIHOOD:
            c["likelihood"] = "medium"
    return r


def diagnose(sketch, diagram="", pin_table="", symptom="", lang="English", serial_log=""):
    prompt, findings = build_prompt(sketch, diagram, pin_table, symptom, serial_log)
    result, model = generate_any(prompt, SYSTEM.replace("{lang}", lang), SCHEMA, parse=parse_result)
    result["rule_findings"] = findings
    result["model"] = model
    return result
