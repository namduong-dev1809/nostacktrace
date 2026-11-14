import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from checks import run_checks  # noqa: E402

ESP = {"type": "board-esp32-devkit-c-v4", "id": "esp"}
UNO = {"type": "wokwi-arduino-uno", "id": "uno"}


def diagram(parts, conns):
    return json.dumps({"version": 1, "parts": parts, "connections": [[a, b, "green", []] for a, b in conns]})


def ids(findings):
    return sorted(f["id"] for f in findings)


SONAR_DIAGRAM = diagram(
    [ESP, {"type": "wokwi-hc-sr04", "id": "ultrasonic1"}],
    [("ultrasonic1:VCC", "esp:5V"), ("ultrasonic1:GND", "esp:GND.1"),
     ("ultrasonic1:TRIG", "esp:5"), ("ultrasonic1:ECHO", "esp:18")])

SONAR_CODE = """
#define TRIG 5
const int ECHO = 18;
void setup() { pinMode(TRIG, OUTPUT); pinMode(ECHO, INPUT); }
void loop() {
  digitalWrite(TRIG, HIGH); delayMicroseconds(10); digitalWrite(TRIG, LOW);
  long d = pulseIn(ECHO, HIGH%s);  // story bug
}
"""


class TestChecks(unittest.TestCase):
    def test_story_pulsein_without_timeout(self):
        self.assertEqual(ids(run_checks(SONAR_CODE % "", SONAR_DIAGRAM)), ["pulsein-no-timeout"])

    def test_pulsein_with_timeout_is_clean(self):
        self.assertEqual(run_checks(SONAR_CODE % ", 30000", SONAR_DIAGRAM), [])

    def test_uno_pin13_has_onboard_led(self):
        code = "void setup() { pinMode(13, OUTPUT); }\nvoid loop() { digitalWrite(13, HIGH); }"
        self.assertEqual(run_checks(code, diagram([UNO], [])), [])

    def test_pin_in_code_not_wired(self):
        code = (SONAR_CODE % ", 30000").replace("const int ECHO = 18", "const int ECHO = 19")
        self.assertEqual(ids(run_checks(code, SONAR_DIAGRAM)), ["pin-not-wired"])

    def test_esp32_input_only_output(self):
        d = diagram([ESP, {"type": "wokwi-led", "id": "led1"}, {"type": "wokwi-resistor", "id": "r1"}],
                    [("esp:34", "r1:1"), ("r1:2", "led1:A"), ("led1:C", "esp:GND.1")])
        code = "void setup(){pinMode(34, OUTPUT);} void loop(){digitalWrite(34, HIGH);}"
        self.assertEqual(ids(run_checks(code, d)), ["esp32-input-only"])

    def test_led_without_resistor(self):
        d = diagram([UNO, {"type": "wokwi-led", "id": "led1"}],
                    [("uno:13", "led1:A"), ("led1:C", "uno:GND.1")])
        code = "void setup(){pinMode(13, OUTPUT);} void loop(){digitalWrite(13, HIGH);}"
        self.assertEqual(ids(run_checks(code, d)), ["led-no-resistor"])

    def test_floating_button_and_pullup_fix(self):
        d = diagram([UNO, {"type": "wokwi-pushbutton", "id": "btn1"}],
                    [("uno:2", "btn1:1.l"), ("btn1:2.r", "uno:GND.2")])
        floating = "void setup(){pinMode(2, INPUT);} void loop(){digitalRead(2);}"
        self.assertEqual(ids(run_checks(floating, d)), ["floating-button"])
        self.assertEqual(run_checks(floating.replace("INPUT)", "INPUT_PULLUP)"), d), [])

    def test_dht_read_too_fast(self):
        d = diagram([UNO, {"type": "wokwi-dht22", "id": "dht1"}], [("dht1:SDA", "uno:2")])
        code = "#include <DHT.h>\nDHT dht(2, DHT22);\nvoid loop(){ dht.readTemperature(); delay(500); }"
        self.assertEqual(ids(run_checks(code, d)), ["dht-too-fast"])

    def test_adc2_with_wifi(self):
        d = diagram([ESP, {"type": "wokwi-potentiometer", "id": "pot1"}], [("pot1:SIG", "esp:25")])
        code = "void setup(){WiFi.begin(\"x\", \"y\");} void loop(){analogRead(25);}"
        self.assertEqual(ids(run_checks(code, d)), ["esp32-adc2-wifi"])

    def test_lcd_i2c_address(self):
        d = diagram([UNO, {"type": "wokwi-lcd1602", "id": "lcd1", "attrs": {"pins": "i2c"}}],
                    [("lcd1:SDA", "uno:A4"), ("lcd1:SCL", "uno:A5")])
        self.assertEqual(ids(run_checks("LiquidCrystal_I2C lcd(0x3F, 16, 2);", d)), ["i2c-address"])
        self.assertEqual(run_checks("LiquidCrystal_I2C lcd(0x27, 16, 2);", d), [])

    def test_no_board_is_an_error(self):
        with self.assertRaises(ValueError):
            run_checks("", diagram([{"type": "wokwi-led", "id": "led1"}], []))


if __name__ == "__main__":
    unittest.main()
