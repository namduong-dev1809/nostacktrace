import hashlib
import json
import os
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).parent
# Local runs read the key from .env; on Hugging Face it comes from Space Secrets.
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

from checks import run_checks  # noqa: E402
from diagnose import MODEL, diagnose  # noqa: E402

CACHE = ROOT / "cache"
EXAMPLES = {p.name: p for p in sorted((ROOT / "examples").iterdir()) if p.is_dir()}
LANGS = {"English": "English", "Tiếng Việt": "Vietnamese"}


def render(result, note=""):
    md = [f"### {result.get('summary', '')}"] if result.get("summary") else []
    for i, c in enumerate(result.get("causes", []), 1):
        md.append(f"**{i}. {c['title']}**  \n`{c['category']}` · likelihood **{c['likelihood']}** · source `{c['source']}`\n\n"
                  f"- **Why:** {c['why']}\n- **Check:** {c['check']}\n- **Fix:** {c['fix']}")
    if not result.get("causes"):
        for f in result.get("rule_findings", []):
            md.append(f"**{f['title']}** (`rule:{f['id']}`)\n\n- {f['evidence']}\n- **Fix:** {f['fix']}")
    if note:
        md.append(f"> {note}")
    return "\n\n".join(md) or "No cause found."


def run(sketch, diagram, pin_table, symptom, lang, mode):
    if not sketch.strip() or not symptom.strip():
        return "Paste your code and describe what you see."
    if mode == "Wokwi project" and not diagram.strip():
        return "Paste diagram.json, or switch to the Real hardware tab."
    if mode != "Wokwi project":
        diagram = ""
    key = hashlib.sha256(json.dumps([sketch, diagram, pin_table, symptom, lang, MODEL]).encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.json"
    if cached.exists():
        return render(json.loads(cached.read_text()))
    try:
        result = diagnose(sketch, diagram, pin_table, symptom, LANGS[lang])
    except ValueError as e:  # bad diagram.json
        return f"Could not read diagram.json: {e}"
    except Exception as e:  # Gemini down or out of quota: still show what the code checks found
        findings = run_checks(sketch, diagram) if diagram else []
        return render({"rule_findings": findings}, f"AI explanation unavailable ({type(e).__name__}). Showing code-check results only.")
    CACHE.mkdir(exist_ok=True)
    cached.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return render(result)


def load_example(name):
    p = EXAMPLES[name]
    return [(p / f).read_text() for f in ("sketch.ino", "diagram.json", "symptom.txt")]


with gr.Blocks(title="NoStackTrace") as demo:
    gr.Markdown("# NoStackTrace\nSoftware bugs give you a stack trace. Hardware bugs give you a dark LED.\n"
                "Paste your Arduino Uno / ESP32 lab project and what you see. Code checks run first, then AI ranks the likely causes.")
    with gr.Row():
        example = gr.Dropdown(list(EXAMPLES), label="Try an example", value=None)
        lang = gr.Radio(list(LANGS), value="English", label="Answer language")
    symptom = gr.Textbox(label="What do you see?", lines=2)
    sketch = gr.Code(label="sketch.ino", language="cpp")
    mode = gr.State("Wokwi project")
    with gr.Tabs():
        with gr.Tab("Wokwi project") as t1:
            diagram = gr.Code(label="diagram.json", language="json")
        with gr.Tab("Real hardware") as t2:
            pin_table = gr.Textbox(label="Pin table", lines=5,
                                   placeholder="GPIO5 -> HC-SR04 TRIG\nGPIO18 -> HC-SR04 ECHO\n5V -> HC-SR04 VCC")
    t1.select(lambda: "Wokwi project", None, mode)
    t2.select(lambda: "Real hardware", None, mode)
    go = gr.Button("Find the bug", variant="primary")
    out = gr.Markdown()

    example.change(load_example, example, [sketch, diagram, symptom])
    go.click(run, [sketch, diagram, pin_table, symptom, lang, mode], out)

if __name__ == "__main__":
    demo.launch()
