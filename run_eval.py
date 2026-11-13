"""Score NoStackTrace against plain Gemini chat on the independent eval set.

usage: python run_eval.py dev|test

Both arms get the same sketch, diagram.json and symptom, and use the same Gemini model.
A Gemini judge compares each answer with the answer key. The answer key is read only by
this script; for the test split only aggregate scores are printed.
Results are saved after every circuit, so a run interrupted by rate limits can resume.
"""
import json
import sys
import time
from pathlib import Path

import app  # noqa: F401  loads .env
import diagnose

ROOT = Path(__file__).parent
EVAL = ROOT / "eval"

BASELINE_PROMPT = """I'm a student. My Wokwi Arduino/ESP32 project doesn't work.

What I see: {symptom}

sketch.ino:
```cpp
{sketch}
```

diagram.json:
```json
{diagram}
```

What is wrong and how do I fix it?"""

JUDGE_PROMPT = """You grade a debugging answer against the known root cause.

Known root cause: {root_cause}
Known fix: {fix}

Answer to grade:
{answer}

top1: does the answer's FIRST / main diagnosis identify this root cause (same underlying fault; wording may differ)?
any: does the answer identify this root cause anywhere, as a stated likely cause (not just a passing mention)?"""

JUDGE_SCHEMA = {"type": "object", "properties": {"top1": {"type": "boolean"}, "any": {"type": "boolean"}, "note": {"type": "string"}},
                "required": ["top1", "any", "note"]}


def call(model, prompt, schema=None):
    """Same model as the NoStackTrace arm, so both arms are comparable."""
    for attempt in range(4):
        try:
            return diagnose.generate(model, prompt, schema=schema)
        except diagnose.Retryable as e:  # busy / rate limited: wait and retry the same model
            if attempt == 3:
                raise
            print(f"   retry {attempt + 1} after {e}", flush=True)
            time.sleep(20 * (attempt + 1))


def nst_text(r):
    return "\n".join(f"{i}. {c['title']} — {c['why']} Fix: {c['fix']}" for i, c in enumerate(r["causes"], 1)) or r["summary"]


def main(split):
    answers = {a["id"]: a for a in json.loads((EVAL / f"{split}_answers.json").read_text())}
    out_path = EVAL / "results" / f"{split}.json"
    out_path.parent.mkdir(exist_ok=True)
    results = json.loads(out_path.read_text()) if out_path.exists() else {}
    for cid, key in answers.items():
        if cid in results:
            continue
        c = EVAL / "circuits" / cid
        sketch, diagram, symptom = [(c / f).read_text() for f in ("sketch.ino", "diagram.json", "symptom.md")]
        print(cid, flush=True)
        nst = diagnose.diagnose(sketch, diagram, "", symptom, "English")
        model = nst["model"]
        base = call(model, BASELINE_PROMPT.format(symptom=symptom, sketch=sketch, diagram=diagram))
        grade = {}
        for arm, text in (("nostacktrace", nst_text(nst)), ("baseline", base)):
            grade[arm] = json.loads(call(model, JUDGE_PROMPT.format(root_cause=key["root_cause"], fix=key["fix"], answer=text), JUDGE_SCHEMA))
        results[cid] = {"model": model, "category": key["category"], "grade": grade,
                        "nostacktrace": nst, "baseline": base}
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1))
        if split == "dev":
            print("   ", {a: (g["top1"], g["any"]) for a, g in grade.items()}, flush=True)

    n = len(results)
    for arm in ("nostacktrace", "baseline"):
        t1 = sum(r["grade"][arm]["top1"] for r in results.values())
        an = sum(r["grade"][arm]["any"] for r in results.values())
        print(f"{split} {arm:13s} top-1 {t1}/{n}   found anywhere {an}/{n}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
