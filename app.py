import hashlib
import html
import json
import os
import re
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).parent
# Local runs read the key from .env; on Hugging Face it comes from Space Secrets.
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

from checks import Diagram, run_checks  # noqa: E402
from nst_trace import check_trace, instrument, parse_log  # noqa: E402
from diagnose import DATASHEETS, MODEL, diagnose  # noqa: E402

CACHE = ROOT / "cache"
EXAMPLES = {p.name: p for p in sorted((ROOT / "examples").iterdir()) if p.is_dir()}
LANGS = {"English": "English", "Tiếng Việt": "Vietnamese"}
SOURCE_LABEL = {"rule": "Verified by code check", "datasheet": "Datasheet", "reasoning": "AI reasoning"}

CSS = """
.gradio-container { max-width: 1240px !important; width: 100% !important; box-sizing: border-box; margin: 0 auto !important; }
footer { display: none !important; }
:root {
  --nst-card: #ffffff; --nst-border: #e4e7ec; --nst-muted: #667085; --nst-text: #101828;
  --nst-accent: #4f46e5; --nst-accent-soft: #eef2ff;
  --nst-high: #b42318; --nst-high-bg: #fef3f2; --nst-med: #b54708; --nst-med-bg: #fffaeb;
  --nst-low: #475467; --nst-low-bg: #f2f4f7; --nst-ok: #067647; --nst-ok-bg: #ecfdf3;
}
.dark {
  --nst-card: #161b26; --nst-border: #2a3142; --nst-muted: #98a2b3; --nst-text: #f5f5f6;
  --nst-accent: #a5b4fc; --nst-accent-soft: #1e1b4b;
  --nst-high: #fda29b; --nst-high-bg: #3b1513; --nst-med: #fec84b; --nst-med-bg: #3a2a0a;
  --nst-low: #cecfd2; --nst-low-bg: #22262f; --nst-ok: #75e0a7; --nst-ok-bg: #0b2e1d;
}
.nst-hero { padding: 8px 4px 4px; }
.nst-hero h1 { margin: 0; font-size: 30px; font-weight: 750; letter-spacing: -0.02em; color: var(--nst-text); }
.nst-hero p { margin: 6px 0 0; color: var(--nst-muted); font-size: 15px; }
.nst-pill { display: inline-block; margin-left: 10px; padding: 2px 10px; border-radius: 999px; font-size: 12px;
  font-weight: 600; vertical-align: middle; background: var(--nst-accent-soft); color: var(--nst-accent); }
#nst-lang { padding-top: 14px; }
.nst-step { margin-bottom: -6px !important; font-size: 13px; font-weight: 650; color: var(--nst-muted); text-transform: uppercase; letter-spacing: .06em; margin: 4px 0 -4px; }
.nst-empty { border: 1.5px dashed var(--nst-border); border-radius: 14px; padding: 36px 24px; text-align: center; color: var(--nst-muted); }
.nst-empty b { display: block; color: var(--nst-text); font-size: 16px; margin-bottom: 6px; }
.nst-summary { background: var(--nst-accent-soft); color: var(--nst-text); border-radius: 12px; padding: 14px 16px; margin-bottom: 14px; line-height: 1.55; }
.nst-card { background: var(--nst-card); border: 1px solid var(--nst-border); border-radius: 14px; padding: 16px 18px; margin-bottom: 12px; }
.nst-card-head { display: flex; gap: 12px; align-items: flex-start; }
.nst-rank { flex: none; width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center;
  font-weight: 700; font-size: 14px; background: var(--nst-accent-soft); color: var(--nst-accent); }
.nst-title { font-weight: 650; font-size: 15.5px; color: var(--nst-text); line-height: 1.4; }
.nst-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.nst-badge { font-size: 12px; font-weight: 600; padding: 2px 9px; border-radius: 999px; }
.nst-high { color: var(--nst-high); background: var(--nst-high-bg); }
.nst-medium { color: var(--nst-med); background: var(--nst-med-bg); }
.nst-low { color: var(--nst-low); background: var(--nst-low-bg); }
.nst-rule { color: var(--nst-ok); background: var(--nst-ok-bg); }
.nst-cat { color: var(--nst-muted); background: var(--nst-low-bg); }
.nst-badge a { color: inherit; text-decoration: underline dotted; }
.nst-rows { margin: 12px 0 0 40px; display: grid; gap: 8px; }
.nst-row { color: var(--nst-text); line-height: 1.55; font-size: 14.5px; }
.nst-row span { display: inline-block; min-width: 52px; font-weight: 650; color: var(--nst-muted); font-size: 12.5px; text-transform: uppercase; letter-spacing: .04em; }
.nst-card code, .nst-summary code { font-size: 13px; padding: 1px 6px; border-radius: 6px; background: var(--nst-low-bg); }
.nst-note { color: var(--nst-med); background: var(--nst-med-bg); border-radius: 10px; padding: 10px 14px; font-size: 14px; }
.nst-meta { color: var(--nst-muted); font-size: 12px; text-align: right; }
#nst-result { position: sticky; top: 16px; }
.gradio-container .cm-editor { max-width: 100%; }
@media (max-width: 900px) {
  .nst-stack { flex-direction: column !important; }
  .nst-stack > * { width: 100% !important; min-width: 0 !important; flex: none !important; }
  #nst-result { position: static; }
  #nst-lang { padding-top: 0; }
  .nst-hero h1 { font-size: 24px; }
  .nst-rows { margin-left: 0; }
}
"""

EMPTY = ('<div class="nst-empty"><b>Your diagnosis will appear here</b>'
         'Describe what you see, paste your code and wiring, then press <i>Find the bug</i>.<br>'
         'No project at hand? Pick an example on the left.</div>')


def _fmt(text):
    """Escape model text, then render `inline code`."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(str(text)))


def source_label(source):
    kind, _, key = source.partition(":")
    if kind == "rule" and key.startswith("trace-"):
        return "Seen in runtime trace"
    fact = DATASHEETS.get(key) if kind == "datasheet" else None
    if not fact:
        return SOURCE_LABEL.get(kind, _fmt(kind))
    where = f"p.{fact['page']}" if fact.get("page") else "docs"
    return f'<a href="{html.escape(fact["url"])}" target="_blank" rel="noopener">Datasheet · {_fmt(fact["part"])} {where}</a>'


def render(result, note=""):
    out = []
    if result.get("summary"):
        out.append(f'<div class="nst-summary">{_fmt(result["summary"])}</div>')
    cards = result.get("causes") or [
        dict(title=f["title"], category="code check", likelihood=f["severity"], source=f"rule:{f['id']}",
             why=f["evidence"], check="", fix=f["fix"]) for f in result.get("rule_findings", [])]
    for i, c in enumerate(cards, 1):
        kind = c["source"].split(":", 1)[0]
        lk = c["likelihood"] if c["likelihood"] in ("high", "medium", "low") else "medium"
        rows = "".join(f'<div class="nst-row"><span>{label}</span> {_fmt(c[k])}</div>'
                       for label, k in (("Why", "why"), ("Check", "check"), ("Fix", "fix")) if c.get(k))
        out.append(
            f'<div class="nst-card"><div class="nst-card-head"><div class="nst-rank">{i}</div><div>'
            f'<div class="nst-title">{_fmt(c["title"])}</div><div class="nst-badges">'
            f'<span class="nst-badge nst-{lk}">{lk} likelihood</span>'
            f'<span class="nst-badge nst-cat">{_fmt(c["category"])}</span>'
            f'<span class="nst-badge {"nst-rule" if kind == "rule" else "nst-cat"}">{source_label(c["source"])}</span>'
            f'</div></div></div><div class="nst-rows">{rows}</div></div>')
    if not cards and not note:
        out.append('<div class="nst-empty"><b>No likely cause found</b>Add more detail to the symptom, or check the wiring tab.</div>')
    if note:
        out.append(f'<div class="nst-note">{_fmt(note)}</div>')
    if result.get("model"):
        out.append(f'<div class="nst-meta">Explained by {_fmt(result["model"])}</div>')
    return "".join(out)


def notice(text):
    return f'<div class="nst-note">{_fmt(text)}</div>'


def make_trace(sketch, diagram, mode):
    if not sketch.strip():
        return "", notice_md("Paste your code first.")
    board = "uno"
    if mode == "wokwi" and diagram.strip():
        try:
            board = Diagram(diagram).board or "uno"
        except ValueError:
            pass
    try:
        traced, baud = instrument(sketch, board)
    except ValueError as e:
        return "", notice_md(str(e))
    return traced, (f"**Run this traced copy** in Wokwi or on your board for about 10 seconds, reproduce the problem, "
                    f"then copy everything from the Serial Monitor (baud **{baud}**) into the box below. "
                    "Your original line numbers are kept.")


def notice_md(text):
    return f"**{text}**"


def run(sketch, diagram, pin_table, symptom, lang, mode, serial_log=""):
    if not sketch.strip() or not symptom.strip():
        return notice("Describe what you see and paste your code first.")
    if mode == "wokwi" and not diagram.strip():
        return notice("Paste diagram.json, or switch to the Real hardware tab.")
    if mode != "wokwi":
        diagram = ""
    key = hashlib.sha256(json.dumps([sketch, diagram, pin_table, symptom, lang, MODEL] + ([serial_log] if serial_log.strip() else [])).encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.json"
    if cached.exists():
        return render(json.loads(cached.read_text()))
    try:
        result = diagnose(sketch, diagram, pin_table, symptom, LANGS[lang], serial_log)
    except ValueError as e:  # bad diagram.json
        return notice(f"Could not read diagram.json: {e}")
    except Exception as e:  # Gemini down or out of quota: still show what the code checks found
        findings = (run_checks(sketch, diagram) if diagram else []) + (
            check_trace(parse_log(serial_log), sketch) if serial_log.strip() else [])
        return render({"rule_findings": findings},
                      f"AI explanation unavailable right now ({type(e).__name__}). Showing code-check results only.")
    CACHE.mkdir(exist_ok=True)
    cached.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return render(result)


def example_title(p):
    t = (p / "title.txt")
    return t.read_text().strip() if t.exists() else p.name.replace("-", " ").capitalize()


def load_example(name):
    p = EXAMPLES[name]
    log = p / "serial_log.txt"
    return [*((p / f).read_text() for f in ("symptom.txt", "sketch.ino", "diagram.json")), gr.Tabs(selected="wokwi"), "wokwi",
            log.read_text() if log.exists() else "", EMPTY]


THEME = gr.themes.Soft(primary_hue="indigo", neutral_hue="slate", radius_size="lg",
                       font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
                       font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"])

with gr.Blocks(title="NoStackTrace") as demo:
    with gr.Row(equal_height=False, elem_classes="nst-stack"):
        gr.HTML('<div class="nst-hero"><h1>NoStackTrace<span class="nst-pill">Arduino Uno · ESP32</span></h1>'
                '<p>Software bugs give you a stack trace. Hardware bugs give you a dark LED. '
                'Code checks run first, then AI ranks the likely causes.</p></div>', padding=False)
        with gr.Column(scale=0, min_width=230, elem_id="nst-lang"):
            gr.HTML('<div class="nst-step">Answer language</div>', padding=False)
            lang = gr.Radio(list(LANGS), value="English", show_label=False, container=False)

    with gr.Row(equal_height=False, elem_classes="nst-stack"):
        with gr.Column(scale=6, min_width=0):
            gr.HTML('<div class="nst-step">Try an example</div>', padding=False)
            with gr.Row():
                ex_buttons = {name: gr.Button(example_title(p), size="sm", variant="secondary")
                              for name, p in EXAMPLES.items()}
            gr.HTML('<div class="nst-step">1 · What do you see?</div>', padding=False)
            symptom = gr.Textbox(show_label=False, lines=2,
                                 placeholder="e.g. The LED never turns on. / Robot đứng khựng rồi đâm vào tường.")
            gr.HTML('<div class="nst-step">2 · Your code</div>', padding=False)
            sketch = gr.Code(show_label=False, language="cpp", lines=12, max_lines=16)
            gr.HTML('<div class="nst-step">3 · Your wiring</div>', padding=False)
            mode = gr.State("wokwi")
            with gr.Tabs(selected="wokwi") as tabs:
                with gr.Tab("Wokwi diagram.json", id="wokwi") as t1:
                    diagram = gr.Code(show_label=False, language="json", lines=8, max_lines=12)
                with gr.Tab("Real hardware", id="real") as t2:
                    pin_table = gr.Textbox(show_label=False, lines=6,
                                           placeholder="One wire per line:\nGPIO5 -> HC-SR04 TRIG\nGPIO18 -> HC-SR04 ECHO\n5V -> HC-SR04 VCC\nGND -> HC-SR04 GND")
            t1.select(lambda: "wokwi", None, mode)
            t2.select(lambda: "real", None, mode)
            gr.HTML('<div class="nst-step">4 · Trace it <span class="nst-pill">recommended</span></div>', padding=False)
            with gr.Accordion("See what really happens when your code runs", open=False):
                gr.Markdown("Reading code only lets AI guess. A trace records every pin read/write, "
                            "`pulseIn()` duration, I2C scan and the slowest `loop()` while your sketch runs.")
                trace_btn = gr.Button("1. Make a traced copy of my sketch", size="sm")
                trace_help = gr.Markdown()
                traced = gr.Code(show_label=False, language="cpp", lines=6, max_lines=12, interactive=False)
                serial_log = gr.Textbox(label="2. Paste the Serial Monitor output here", lines=5,
                                        placeholder="NST|start|board=esp32\nNST|t=1052|L17|pulseIn(18)=0|took_us=1000214\n...")
            with gr.Row():
                clear = gr.Button("Clear", variant="secondary", scale=1)
                go = gr.Button("Find the bug", variant="primary", scale=3)
        with gr.Column(scale=5, min_width=0, elem_id="nst-result"):
            gr.HTML('<div class="nst-step">Diagnosis</div>', padding=False)
            out = gr.HTML(EMPTY)

    for name, btn in ex_buttons.items():
        btn.click(lambda n=name: load_example(n), None, [symptom, sketch, diagram, tabs, mode, serial_log, out])
    trace_btn.click(make_trace, [sketch, diagram, mode], [traced, trace_help])
    go.click(run, [sketch, diagram, pin_table, symptom, lang, mode, serial_log], out).then(
        None, None, None, js="() => { if (innerWidth < 900) document.getElementById('nst-result').scrollIntoView({behavior: 'smooth'}); }")
    clear.click(lambda: ["", "", "", "", "", "", "", EMPTY], None,
                [symptom, sketch, diagram, pin_table, traced, trace_help, serial_log, out])

if __name__ == "__main__":
    demo.launch(theme=THEME, css=CSS, footer_links=[],
                head='<meta name="viewport" content="width=device-width, initial-scale=1">')
