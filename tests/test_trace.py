import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nst_trace import check_trace, instrument, parse_log  # noqa: E402

SKETCH = """#include <ESP32Servo.h>
#define ECHO 18
void setup() {
  Serial.begin(9600);
  pinMode(ECHO, INPUT);
}
void loop() {
  long us = pulseIn(ECHO, HIGH);
}
"""

FREEZE_LOG = """NST|start|board=esp32
NST|t=51|L5|pinMode(18,0)
NST|setup_done
NST|t=1052|L8|pulseIn(18)=0|took_us=1000214
NST|t=1052|loop_slowest_us=1000890|loops=1
my own print
"""


def ids(findings):
    return [f["id"] for f in findings]


class TestInstrument(unittest.TestCase):
    def test_keeps_user_baud_and_line_numbers(self):
        traced, baud = instrument(SKETCH, "esp32")
        self.assertEqual(baud, 9600)
        self.assertIn("Serial.begin(9600)", traced)
        # header after the includes, then #line restores the student's numbering for the code below
        self.assertLess(traced.index("#include <ESP32Servo.h>"), traced.index("NoStackTrace trace header"))
        self.assertIn("#line 2\n#define ECHO 18", traced)

    def test_i2c_scan_only_with_default_wire_pins(self):
        self.assertIn("i2c_scan", instrument("#include <Wire.h>\nvoid setup(){Wire.begin();}\nvoid loop(){}")[0])
        self.assertNotIn("i2c_scan", instrument("#include <Wire.h>\nvoid setup(){Wire.begin(4, 5);}\nvoid loop(){}")[0])

    def test_io_wrappers_do_not_print(self):
        # Printing inside digitalWrite() delayed pulseIn() enough to miss the echo (seen in Wokwi).
        traced = instrument(SKETCH, "esp32")[0]
        for fn in ("nst_dr", "nst_dw", "nst_ar", "nst_pm", "nst_pi_core"):
            body = traced.split(f" {fn}(int")[1].split("\n}")[0]
            self.assertNotIn("Serial", body, fn)
        self.assertIn("nst_user_loop();\n  unsigned long dt = micros() - t0;\n  nst_flush();", traced)

    def test_library_loop_methods_keep_their_name(self):
        traced = instrument("#include <PubSubClient.h>\nPubSubClient client;\nvoid setup() {}\nvoid loop() { client.loop(); }", "esp32")[0]
        self.assertIn("void nst_user_loop() { client.loop(); }", traced)
        self.assertNotIn("#define loop", traced)

    def test_header_outside_conditional_includes_and_comments(self):
        sk = "#ifdef ESP32\n#include <WiFi.h>\n#endif\n/*\n#include <Old.h>\n*/\nvoid setup() {}\nvoid loop() {}"
        traced = instrument(sk, "uno")[0]
        self.assertLess(traced.index("#endif"), traced.index("NoStackTrace trace header"))
        self.assertLess(traced.index("NoStackTrace trace header"), traced.index("#include <Old.h>"))
        self.assertIn("#line 4\n/*", traced)

    def test_baud_from_define_and_not_software_serial(self):
        self.assertEqual(instrument("#define BAUD 9600\nvoid setup() { Serial.begin(BAUD); }\nvoid loop() {}")[1], 9600)
        self.assertEqual(instrument("void setup() { gps.begin(9600); // Serial.begin(4800);\n}\nvoid loop() {}")[1], 115200)

    def test_needs_setup_and_loop(self):
        with self.assertRaises(ValueError):
            instrument("void setup(){}")


class TestTraceChecks(unittest.TestCase):
    def test_parse(self):
        ev = parse_log(FREEZE_LOG)
        self.assertEqual(len(ev), 5)
        self.assertEqual(ev[3], {"t_ms": 1052, "line": 8, "call": "pulseIn(18)=0", "took_us": 1000214})

    def test_pulsein_freeze_found(self):
        self.assertEqual(ids(check_trace(parse_log(FREEZE_LOG))), ["trace-pulsein-timeout"])

    def test_setup_stuck(self):
        self.assertEqual(ids(check_trace(parse_log("NST|start|board=uno\nNST|t=5|L3|pinMode(2,0)\n"))), ["trace-setup-stuck"])

    def test_i2c_address_from_scan(self):
        log = "NST|start|board=uno\nNST|i2c_scan=0x3F \nNST|setup_done\n"
        self.assertEqual(ids(check_trace(parse_log(log), "LiquidCrystal_I2C lcd(0x27, 16, 2);")), ["trace-i2c-address"])
        self.assertEqual(check_trace(parse_log(log), "LiquidCrystal_I2C lcd(0x3F, 16, 2);"), [])

    def test_real_wokwi_logs(self):
        ex = Path(__file__).parent.parent / "examples"
        for name, want in (("maze-sonar", ["trace-pulsein-timeout"]), ("lazy-button", ["trace-slow-loop"]),
                           ("blank-lcd", ["trace-i2c-address"])):  # blank-lcd also has a 0.5 s delay() loop: not slow
            log, sketch = (ex / name / "serial_log.txt").read_text(), (ex / name / "sketch.ino").read_text()
            self.assertEqual(ids(check_trace(parse_log(log), sketch)), want, name)

    def test_garbled_and_partial_logs(self):
        self.assertEqual(check_trace(parse_log("NST|t=5|L3|pulseIn(7)=0|took_us=12.5")), [])  # wrong baud
        self.assertEqual(check_trace(parse_log("NST|t=5|L3|digitalWrite(1,1)")), [])  # tail only, no NST|start
        self.assertEqual(ids(check_trace(parse_log("NST|start|board=uno\nNST|dropped=40\nNST|setup_done"))), ["trace-dropped"])

    def test_i2c_ignores_unrelated_hex_and_pads(self):
        log = "NST|start|board=uno\nNST|i2c_scan=0x8 \nNST|setup_done\n"
        self.assertEqual(check_trace(parse_log(log), "uint8_t mask = 0xFF; Wire.beginTransmission(0x08);"), [])

    def test_empty_log_no_findings(self):
        self.assertEqual(check_trace(parse_log("")), [])


if __name__ == "__main__":
    unittest.main()
