"""Deterministic checks on a Wokwi project: code decides, the AI only explains.

Each check returns findings as dicts:
{"id", "severity": "high"|"medium", "title", "evidence", "fix"}
"""
import json
import re

ESP32_INPUT_ONLY = {"34", "35", "36", "39"}
ESP32_ADC2 = {"0", "2", "4", "12", "13", "14", "15", "25", "26", "27"}
OUTPUT_CALLS = ("digitalWrite", "analogWrite", "tone", "ledcAttachPin")


# ---------- diagram.json ----------

def _board(parts):
    for p in parts:
        t = p["type"]
        if "arduino-uno" in t:
            return p["id"], "uno"
        if "esp32" in t:
            return p["id"], "esp32"
    return None, None


def norm_pin(pin, board, board_type=""):
    """Board pin name -> canonical form shared by diagram and code ("13", "A0", "GND")."""
    pin = pin.upper()
    if pin.startswith("GND"):
        return "GND"
    if board == "esp32":
        pin = {"VP": "36", "VN": "39"}.get(pin, pin)
        # Only the old DevKit V1 labels GPIOs "D2"; on DevKitC V4, D0-D3 are flash pins.
        prefix = "GPIO|D" if "devkit-v1" in board_type else "GPIO"
        pin = re.sub(rf"^({prefix})(\d+)$", r"\2", pin)
    return pin


class Diagram:
    def __init__(self, text):
        d = json.loads(text)
        self.parts = {p["id"]: p for p in d.get("parts", [])}
        self.board_id, self.board = _board(d.get("parts", []))
        self.board_type = self.parts[self.board_id]["type"] if self.board_id else ""
        self._parent = {}
        for conn in d.get("connections", []):
            self._union(conn[0], conn[1])
        # Pushbutton legs on the same side are one conductor inside the part.
        for pid, p in self.parts.items():
            if p["type"] == "wokwi-pushbutton":
                self._union(f"{pid}:1.l", f"{pid}:1.r")
                self._union(f"{pid}:2.l", f"{pid}:2.r")
        # shortcut: breadboard ("wokwi-breadboard") internal rails are not modelled; add when an eval circuit needs it.

    def _find(self, x):
        self._parent.setdefault(x, x)
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def _union(self, a, b):
        self._parent[self._find(a)] = self._find(b)

    def net(self, endpoint):
        root = self._find(endpoint)
        return {e for e in self._parent if self._find(e) == root}

    def nets(self):
        groups = {}
        for e in self._parent:
            groups.setdefault(self._find(e), set()).add(e)
        return list(groups.values())

    def summary(self):
        """One line per electrical net, e.g. 'uno:13 -- r1:1 (wokwi-resistor)'."""
        def label(e):
            pid = e.split(":", 1)[0]
            return e if pid == self.board_id else f"{e} ({self.parts.get(pid, {}).get('type', '?')})"
        return "\n".join(" -- ".join(sorted(map(label, n))) for n in self.nets())

    def board_pins(self, net):
        """Canonical board pins in a net."""
        return {norm_pin(e.split(":", 1)[1], self.board, self.board_type) for e in net
                if e.split(":", 1)[0] == self.board_id}

    def board_net(self, pin):
        for e in list(self._parent):
            pid, p = e.split(":", 1)
            if pid == self.board_id and norm_pin(p, self.board, self.board_type) == pin:
                return self.net(e)
        return set()

    def has_part_type(self, net, type_):
        return any(self.parts.get(e.split(":", 1)[0], {}).get("type") == type_ for e in net)

    def of_type(self, type_):
        return [pid for pid, p in self.parts.items() if p["type"] == type_]


# ---------- sketch.ino ----------

def _strip_comments(code):
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    return re.sub(r"//[^\n]*", "", code)


class Sketch:
    def __init__(self, text):
        self.code = _strip_comments(text)
        self.consts = dict(re.findall(r"#define\s+(\w+)\s+(\w+)", self.code))
        self.consts.update(re.findall(
            r"(?:const\s+)?(?:int|byte|uint8_t|short|long)\s+(\w+)\s*=\s*(\w+)\s*;", self.code))

    def pin(self, arg):
        arg = arg.strip()
        for _ in range(3):  # follow NAME -> OTHER_NAME -> 13
            arg = self.consts.get(arg, arg)
        return re.sub(r"^GPIO_NUM_", "", arg).upper()

    def calls(self, name):
        """Argument lists of every call to `name(...)` or `obj.name(...)`."""
        return [[a.strip() for a in args.split(",")]
                for args in re.findall(rf"\b{name}\s*\(([^()]*)\)", self.code)]

    def pin_modes(self):
        return {self.pin(a[0]): a[1] for a in self.calls("pinMode") if len(a) == 2}

    def used_pins(self):
        pins = set()
        for f in ("pinMode", "digitalWrite", "digitalRead", "analogRead", "analogWrite",
                  "pulseIn", "attach", "tone"):
            pins |= {self.pin(a[0]) for a in self.calls(f) if a and a[0]}
        return {p for p in pins if re.fullmatch(r"A?\d+", p)}

    def output_pins(self):
        pins = {p for p, m in self.pin_modes().items() if m == "OUTPUT"}
        for f in OUTPUT_CALLS + ("attach",):
            pins |= {self.pin(a[0]) for a in self.calls(f) if a and a[0]}
        return pins


# ---------- checks ----------

def check_input_only_pins(dg, sk):
    if dg.board != "esp32":
        return []
    out = []
    for p in sorted(sk.output_pins() & ESP32_INPUT_ONLY):
        out.append(dict(id="esp32-input-only", severity="high",
                        title=f"GPIO{p} is input-only on the ESP32",
                        evidence=f"The code drives GPIO{p} as an output.",
                        fix="Move this signal to an output-capable pin such as GPIO 2, 4, 5, 18 or 19."))
    for p, m in sorted(sk.pin_modes().items()):
        if p in ESP32_INPUT_ONLY and m in ("INPUT_PULLUP", "INPUT_PULLDOWN"):
            out.append(dict(id="esp32-no-internal-pull", severity="high",
                            title=f"GPIO{p} has no internal pull resistor",
                            evidence=f"pinMode({p}, {m}) does nothing on GPIO 34-39, so the input floats.",
                            fix="Add an external 10k pull-up/pull-down resistor, or use another GPIO."))
    return out


def check_unwired_pins(dg, sk):
    out = []
    for p in sorted(sk.used_pins()):
        if dg.board == "uno" and p == "13":  # on-board LED "L" is wired to pin 13
            continue
        net = dg.board_net(p)
        if not any(e.split(":", 1)[0] != dg.board_id for e in net):
            out.append(dict(id="pin-not-wired", severity="high",
                            title=f"Pin {p} is used in code but nothing is wired to it",
                            evidence=f"The code uses pin {p}; in diagram.json no part connects to that pin.",
                            fix="Check that the pin number in the code matches the wire, or move the wire."))
    return out


def check_floating_buttons(dg, sk):
    out, modes = [], sk.pin_modes()
    for btn in dg.of_type("wokwi-pushbutton"):
        for side in ("1.l", "2.l"):
            net = dg.net(f"{btn}:{side}")
            for p in dg.board_pins(net) - {"GND", "5V", "3V3", "3.3V", "VIN"}:
                pulled = modes.get(p) in ("INPUT_PULLUP", "INPUT_PULLDOWN") and p not in ESP32_INPUT_ONLY
                if not pulled and not dg.has_part_type(net, "wokwi-resistor"):
                    out.append(dict(id="floating-button", severity="high",
                                    title=f"Button {btn} on pin {p} floats when not pressed",
                                    evidence=f"pinMode is {modes.get(p, 'not set (defaults to INPUT)')} and no resistor is on that net.",
                                    fix=f"Use pinMode({p}, INPUT_PULLUP) and wire the other leg to GND, or add a 10k resistor."))
    return out


def check_led_resistor(dg, sk):
    out = []
    for led in dg.of_type("wokwi-led"):
        a, c = dg.net(f"{led}:A"), dg.net(f"{led}:C")
        drive = dg.board_pins(a) - {"GND"}
        if drive and "GND" in dg.board_pins(c) and not (
                dg.has_part_type(a, "wokwi-resistor") or dg.has_part_type(c, "wokwi-resistor")):
            out.append(dict(id="led-no-resistor", severity="medium",
                            title=f"LED {led} has no current-limiting resistor",
                            evidence=f"The LED goes straight from pin {', '.join(sorted(drive))} to GND.",
                            fix="Add a 220-330 ohm resistor in series. The simulator still lights it; real hardware can burn the LED or the pin."))
    return out


def check_pulsein_timeout(dg, sk):
    if any(len(a) == 2 for a in sk.calls("pulseIn")):
        return [dict(id="pulsein-no-timeout", severity="high",
                     title="pulseIn() has no timeout and can freeze loop() for 1 second",
                     evidence="pulseIn(pin, level) waits up to 1,000,000 us when no echo returns (object out of range).",
                     fix="Pass a timeout: pulseIn(ECHO, HIGH, 30000) caps the wait near 30 ms (about 5 m).")]
    return []


def check_dht_interval(dg, sk):
    if not dg.of_type("wokwi-dht22") or "millis" in sk.code:
        return []
    if not re.search(r"read(Temperature|Humidity)|getTempAndHumidity|\.read\s*\(", sk.code):
        return []
    delays = [int(a[0]) for a in sk.calls("delay") if a and a[0].isdigit()]
    if delays and max(delays) < 2000:
        return [dict(id="dht-too-fast", severity="medium",
                     title="DHT22 is read faster than once every 2 seconds",
                     evidence=f"The longest delay() in the sketch is {max(delays)} ms.",
                     fix="Wait at least 2000 ms between DHT22 reads, e.g. delay(2000) or a millis() timer.")]
    return []


def check_adc2_wifi(dg, sk):
    if dg.board != "esp32" or "WiFi.begin" not in sk.code:
        return []
    bad = sorted({sk.pin(a[0]) for a in sk.calls("analogRead") if a and a[0]} & ESP32_ADC2)
    return [dict(id="esp32-adc2-wifi", severity="high",
                 title=f"analogRead on ADC2 pin {p} fails while WiFi is on",
                 evidence="ADC2 is used by the WiFi driver; reads return errors or stale values.",
                 fix="Move the analog sensor to an ADC1 pin: GPIO 32, 33, 34, 35, 36 or 39.") for p in bad]


def check_i2c_address(dg, sk):
    out = []
    for lcd in dg.of_type("wokwi-lcd1602"):
        attrs = dg.parts[lcd].get("attrs", {})
        if attrs.get("pins") != "i2c":
            continue
        want = attrs.get("i2cAddress", "0x27").lower()
        for got in re.findall(r"LiquidCrystal_I2C\s+\w+\s*\(\s*(0x[0-9A-Fa-f]+)", sk.code):
            if got.lower() != want:
                out.append(dict(id="i2c-address", severity="high",
                                title=f"LCD I2C address mismatch ({got} in code, {want} on the part)",
                                evidence="The LCD only answers on its own address; the screen stays blank.",
                                fix=f"Use {want} in the LiquidCrystal_I2C constructor, or run an I2C scanner."))
    for mpu in dg.of_type("wokwi-mpu6050"):
        ad0_high = bool(dg.board_pins(dg.net(f"{mpu}:AD0")) & {"5V", "3V3", "3.3V", "VIN"})
        want = "0x69" if ad0_high else "0x68"
        used = {a.lower() for a in re.findall(r"0x6[89]", sk.code, flags=re.I)}
        if used and want not in used:
            out.append(dict(id="i2c-address", severity="high",
                            title=f"MPU6050 address mismatch ({', '.join(sorted(used))} in code, {want} by wiring)",
                            evidence=f"AD0 is {'high' if ad0_high else 'low/unconnected'}, so the chip answers on {want}.",
                            fix=f"Use {want} in the code, or rewire AD0."))
    return out


CHECKS = [check_input_only_pins, check_unwired_pins, check_floating_buttons, check_led_resistor,
          check_pulsein_timeout, check_dht_interval, check_adc2_wifi, check_i2c_address]


def run_checks(sketch_text, diagram_text):
    dg, sk = Diagram(diagram_text), Sketch(sketch_text)
    if dg.board is None:
        raise ValueError("diagram.json has no Arduino Uno or ESP32 board part.")
    return [f for check in CHECKS for f in check(dg, sk)]
