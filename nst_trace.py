"""Trace mode: give hardware a stack trace.

instrument(sketch) wraps Arduino I/O calls with macros that print what really happens at
runtime (line, pin, value, duration) to Serial. The student runs the traced sketch in Wokwi
or on the real board and pastes the Serial output back; parse_log() + check_trace() turn it
into evidence. No AI is involved in instrumenting, so the result is the same every time.
"""
import re

# Calls are logged at their 1st, 2nd, 3rd, 4th, 8th, 16th... time per source line,
# so a fast loop() cannot flood Serial. Slow pulseIn() and new slowest loop() are always logged.
# Events are buffered and printed after each loop() pass: printing inside an I/O call takes
# ~1 ms, long enough to miss an HC-SR04 echo and make the trace cause the bug it looks for.
HEADER = r"""
// ---- NoStackTrace trace header (generated; remove when done) ----
struct NstEv { unsigned long t, v, took; int line; char kind; int pin; };
static NstEv nst_buf[24];
static int nst_n;
static unsigned long nst_hits[64], nst_dropped;
static bool nst_want(int line) {
  unsigned long n = ++nst_hits[line & 63];
  return n <= 3 || (n & (n - 1)) == 0;
}
static void nst_add(int line, char kind, int pin, unsigned long v, unsigned long took) {
  if (nst_n < 24) nst_buf[nst_n++] = NstEv{millis(), v, took, line, kind, pin};
  else nst_dropped++;
}
static void nst_flush() {
  for (int i = 0; i < nst_n; i++) {
    NstEv &e = nst_buf[i];
    Serial.print(F("NST|t=")); Serial.print(e.t); Serial.print(F("|L")); Serial.print(e.line); Serial.print('|');
    if (e.kind == 'w') { Serial.print(F("digitalWrite(")); Serial.print(e.pin); Serial.print(','); Serial.print(e.v); Serial.println(')'); continue; }
    if (e.kind == 'm') { Serial.print(F("pinMode(")); Serial.print(e.pin); Serial.print(','); Serial.print(e.v); Serial.println(')'); continue; }
    Serial.print(e.kind == 'r' ? F("digitalRead(") : e.kind == 'a' ? F("analogRead(") : F("pulseIn("));
    Serial.print(e.pin); Serial.print(F(")=")); Serial.print(e.v);
    if (e.kind == 'p') { Serial.print(F("|took_us=")); Serial.print(e.took); }
    Serial.println();
  }
  nst_n = 0;
  if (nst_dropped) { Serial.print(F("NST|dropped=")); Serial.println(nst_dropped); nst_dropped = 0; }
}
static int nst_dr(int pin, int line) {
  int v = (digitalRead)(pin);
  if (nst_want(line)) nst_add(line, 'r', pin, v, 0);
  return v;
}
static void nst_dw(int pin, int val, int line) {
  (digitalWrite)(pin, val);
  if (nst_want(line)) nst_add(line, 'w', pin, val, 0);
}
static int nst_ar(int pin, int line) {
  int v = (analogRead)(pin);
  if (nst_want(line)) nst_add(line, 'a', pin, v, 0);
  return v;
}
static void nst_pm(int pin, int mode, int line) {
  (pinMode)(pin, mode);
  nst_add(line, 'm', pin, mode, 0);
}
static unsigned long nst_pi_core(int line, int pin, int state, unsigned long timeout, bool given) {
  unsigned long t0 = micros();
  unsigned long v = given ? (pulseIn)(pin, state, timeout) : (pulseIn)(pin, state);
  unsigned long dt = micros() - t0;
  if (dt > 100000UL || nst_want(line)) nst_add(line, 'p', pin, v, dt);
  return v;
}
static unsigned long nst_pi(int line, int pin, int state, int) { return nst_pi_core(line, pin, state, 0, false); }
static unsigned long nst_pi(int line, int pin, int state, unsigned long timeout, int) { return nst_pi_core(line, pin, state, timeout, true); }
#define digitalRead(p) nst_dr((p), __LINE__)
#define digitalWrite(p, v) nst_dw((p), (v), __LINE__)
#define analogRead(p) nst_ar((p), __LINE__)
#define pinMode(p, m) nst_pm((p), (m), __LINE__)
#define pulseIn(...) nst_pi(__LINE__, __VA_ARGS__, 0)
// ---- end of trace header ----
"""

FOOTER = r"""
// ---- NoStackTrace trace footer (generated) ----
static unsigned long nst_loops, nst_slowest;
void setup() {
  Serial.begin(%(baud)d);
  delay(50);
  Serial.println(F("NST|start|board=%(board)s"));%(scan)s
  nst_user_setup();
  nst_flush();
  Serial.println(F("NST|setup_done"));
}
void loop() {
  unsigned long t0 = micros();
  nst_user_loop();
  unsigned long dt = micros() - t0;
  nst_flush();
  nst_loops++;
  if (dt > nst_slowest) {
    nst_slowest = dt;
    Serial.print(F("NST|t=")); Serial.print(millis()); Serial.print(F("|loop_slowest_us=")); Serial.print(dt);
    Serial.print(F("|loops=")); Serial.println(nst_loops);
  }
}
"""

I2C_SCAN = r"""
  Wire.begin();
  Serial.print(F("NST|i2c_scan="));
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) { Serial.print(F("0x")); Serial.print(a, HEX); Serial.print(' '); }
  }
  Serial.println();"""


USER_FN = re.compile(r"^void(\s+)(setup|loop)(\s*\()", re.M)


def _strip_comments(code):
    """Blank out comments (keeping newlines) so they are not read as code; string-aware."""
    return re.sub(r'"(?:\\.|[^"\\\n])*"|//[^\n]*|/\*.*?\*/',
                  lambda m: m.group(0) if m.group(0)[0] == '"' else re.sub(r"[^\n]", " ", m.group(0)),
                  code, flags=re.S)


def _baud(code):
    """Baud of the hardware Serial port, resolving a #define or const name; 115200 if unknown."""
    m = re.search(r"(?<![\w.])Serial\.begin\s*\(\s*(\w+)", code)
    if not m:
        return 115200
    if m.group(1).isdigit():
        return int(m.group(1))
    d = re.search(rf"(?:#define\s+{m.group(1)}\s+|\b{m.group(1)}\s*=\s*)(\d+)", code)
    return int(d.group(1)) if d else 115200


def _header_line(code):
    """Index of the line after which the trace header goes: after the last #include,
    and outside any #if block that contains it, so it is never skipped by the preprocessor."""
    lines, depth, last_inc, close = code.split("\n"), 0, -1, -1
    for i, l in enumerate(lines):
        t = l.strip()
        if t.startswith("#include"):
            last_inc, close = i, i if depth == 0 else -1
        elif re.match(r"#\s*if", t):
            depth += 1
        elif re.match(r"#\s*endif", t):
            depth = max(depth - 1, 0)
            if depth == 0 and close == -1 and last_inc >= 0:
                close = i
    return close if last_inc >= 0 else -1


def instrument(sketch, board="uno"):
    """Return (traced_sketch, baud). Raises ValueError if the sketch has no setup()/loop()."""
    sketch = sketch.replace("\r\n", "\n")
    code = _strip_comments(sketch)
    if {m.group(2) for m in USER_FN.finditer(code)} != {"setup", "loop"}:
        raise ValueError("The sketch needs both setup() and loop(), each starting with 'void' at the start of a line.")
    baud = _baud(code)
    # Scan only on the default I2C pins; custom pins (Wire.begin(sda, scl), setPins, Wire1) mean the defaults are wrong.
    scan = I2C_SCAN if "Wire.h" in code and not re.search(r"Wire\.begin\s*\(\s*[^)\s]|Wire\d?\.setPins|\bWire1\b", code) else ""
    lines = sketch.split("\n")
    # Rename only the student's own setup()/loop() definitions (column 0, outside comments), so
    # library methods such as client.loop() keep their names.
    code_lines = code.split("\n")
    lines = [USER_FN.sub(r"void\1nst_user_\2\3", l) if USER_FN.match(c) else l for l, c in zip(lines, code_lines)]
    cut = _header_line(code)
    # The header goes after the includes so library headers are not rewritten by the macros.
    # Its #line directive keeps __LINE__ equal to the student's original line numbers.
    head = "\n".join(lines[:cut + 1])
    body = "\n".join(lines[cut + 1:])
    traced = (f"{head}\n#include <Arduino.h>\n{HEADER}\n#line {cut + 2}\n{body}\n"
              + FOOTER % {"baud": baud, "board": board, "scan": scan})
    return traced, baud


LOG_LINE = re.compile(r"NST\|(.*)")


NUMERIC = ("took_us", "loop_slowest_us", "loops", "dropped")
NUM = re.compile(r"\d{1,12}", re.A)


def parse_log(text):
    """Serial output -> list of dicts, one per NST line. Other lines are the sketch's own prints.
    Fields whose number is cut off or garbled (wrong baud) are dropped, never kept as text."""
    events = []
    for raw in text.splitlines():
        m = LOG_LINE.search(raw)
        if not m:
            continue
        ev = {}
        for part in m.group(1).split("|"):
            k, _, v = part.partition("=")
            if k == "t" and NUM.fullmatch(v):
                ev["t_ms"] = int(v)
            elif re.fullmatch(r"L\d{1,6}", part, re.A):
                ev["line"] = int(part[1:])
            elif k in NUMERIC:
                if NUM.fullmatch(v):
                    ev[k] = int(v)
            elif k in ("board", "i2c_scan"):
                ev[k] = v.split("NST")[0].strip()
            else:
                ev.setdefault("call", part)
        events.append(ev)
    return events


def _i2c_addresses(sketch):
    """Addresses the code itself uses for I2C devices (not every hex constant in the sketch)."""
    pats = (r"LiquidCrystal_I2C\s+\w+\s*\(\s*(0x[0-9a-fA-F]+)",
            r"beginTransmission\s*\(\s*(0x[0-9a-fA-F]+)",
            r"\.begin\s*\([^)]*?(0x[0-9a-fA-F]+)",
            r"#define\s+\w*ADDR\w*\s+(0x[0-9a-fA-F]+)",
            r"\b\w*[Aa]ddr\w*\s*=\s*(0x[0-9a-fA-F]+)")
    return {int(a, 16) for p in pats for a in re.findall(p, sketch)}


def check_trace(events, sketch=""):
    """Deterministic findings from runtime evidence."""
    out = []
    slow = [e for e in events if e.get("took_us", 0) >= 500_000]
    if slow:
        e = max(slow, key=lambda e: e["took_us"])
        out.append(dict(id="trace-pulsein-timeout", severity="high",
                        title=f"pulseIn() on line {e.get('line')} blocked for {e['took_us'] / 1e6:.2f} s",
                        evidence=f"Trace: {e.get('call')} took {e['took_us']} us ({len(slow)} slow call(s) logged).",
                        fix="Pass a timeout as the third argument, e.g. pulseIn(ECHO, HIGH, 30000)."))
    loops = [e for e in events if "loop_slowest_us" in e]
    if loops and loops[-1]["loop_slowest_us"] >= 1_000_000 and not slow:
        e = loops[-1]
        out.append(dict(id="trace-slow-loop", severity="medium",
                        title=f"One pass of loop() took {e['loop_slowest_us'] / 1e6:.2f} s",
                        evidence="Anything that must react quickly (buttons, sensors, motors) waits this long.",
                        fix="Look for delay() or blocking calls in loop(); use millis() timing instead."))
    scans = [e for e in events if "i2c_scan" in e]
    if scans:
        found = {int(a, 16) for a in str(scans[-1]["i2c_scan"]).split() if re.fullmatch(r"0x[0-9a-fA-F]{1,2}", a)}
        wanted = _i2c_addresses(sketch)
        hx = lambda xs: ", ".join(f"0x{a:02X}" for a in sorted(xs))
        if not found:
            out.append(dict(id="trace-i2c-none", severity="high", title="No I2C device answered on the bus",
                            evidence="The I2C scan at startup found no address.",
                            fix="Check SDA/SCL wiring (Uno: A4/A5, ESP32: 21/22), power and GND to the module."))
        elif wanted and not (wanted & found):
            out.append(dict(id="trace-i2c-address", severity="high",
                            title=f"I2C device is at {hx(found)}, code uses {hx(wanted)}",
                            evidence="The startup I2C scan found a device, but not at the address in the code.",
                            fix=f"Change the address in the code to {hx(sorted(found)[:1])}."))
    dropped = sum(e.get("dropped", 0) for e in events)
    if dropped:
        out.append(dict(id="trace-dropped", severity="low", title=f"The trace skipped {dropped} event(s)",
                        evidence="More than 24 traced calls happened in one loop() pass; the extra ones were not logged.",
                        fix="Missing lines in the trace are not proof that a call did not happen."))
    # Only when the log starts at the beginning: a pasted tail has no NST|start line.
    if any(e.get("call") == "start" for e in events) and not any(e.get("call") == "setup_done" for e in events):
        out.append(dict(id="trace-setup-stuck", severity="high", title="setup() never finished",
                        evidence="The trace shows NST|start but no NST|setup_done.",
                        fix="A call in setup() is blocking (e.g. waiting for a sensor, Wire or Serial). Add Serial.println markers in setup() to find it."))
    return out


def summarize(events, limit=60):
    """Compact text of the trace for the AI prompt."""
    keep = events[:limit // 2] + events[-limit // 2:] if len(events) > limit else events
    return "\n".join("NST|" + "|".join(f"{k}={v}" for k, v in e.items()) for e in keep)
