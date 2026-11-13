"""Code checks first, then Gemini explains and covers what the rules cannot see."""
import json
import os
from pathlib import Path

import httpx
from google import genai
from google.genai import errors, types

from checks import Diagram, run_checks

ROOT = Path(__file__).parent
# Tried in order; a busy (503) or rate-limited (429) model falls through to the next one.
MODELS = os.environ.get("GEMINI_MODELS", "gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",")
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
- "Confirmed findings" come from deterministic code checks. Treat them as facts and include each one that can explain the symptom.
- Only cite a datasheet fact from the "Datasheet facts" list, by its key, as source "datasheet:<key>". Never invent page numbers or specs.
- source is "rule:<id>" for a confirmed finding, "datasheet:<key>" for a listed fact, or "reasoning" otherwise.
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


def build_prompt(sketch, diagram, pin_table, symptom):
    findings, parts = [], ""
    if diagram.strip():
        findings = run_checks(sketch, diagram)
        dg = Diagram(diagram)
        parts = f"Board: {dg.board}\nWiring nets:\n{dg.summary()}"
    else:
        parts = f"Pin table typed by the student (real hardware):\n{pin_table}"
    facts = "\n".join(f"- {k}: {v['fact']} ({v['source']}, p.{v['page']})" for k, v in DATASHEETS.items()) or "(none)"
    prompt = f"""Symptom: {symptom}

{parts}

Code:
```cpp
{sketch}
```

Confirmed findings:
{json.dumps(findings, indent=1) if findings else "(none)"}

Datasheet facts:
{facts}"""
    return prompt, findings


def diagnose(sketch, diagram="", pin_table="", symptom="", lang="English"):
    prompt, findings = build_prompt(sketch, diagram, pin_table, symptom)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM.replace("{lang}", lang),
        response_mime_type="application/json",
        response_schema=SCHEMA,
        temperature=0.2,
    )
    for i, model in enumerate(MODELS):
        try:
            resp = _client().models.generate_content(model=model, contents=prompt, config=config)
            break
        except (errors.ServerError, errors.ClientError, httpx.TimeoutException) as e:
            if getattr(e, "code", 504) not in (429, 503, 504, 404) or i == len(MODELS) - 1:
                raise
    result = json.loads(resp.text)
    result["rule_findings"] = findings
    result["model"] = model
    return result
