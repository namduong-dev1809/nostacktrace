"""Check evaluation structure without reading application code or revealing answers."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PINS = {
    "wokwi-arduino-uno": {str(i) for i in range(14)}
    | {f"A{i}" for i in range(6)} | {"GND.1", "GND.2", "GND.3", "5V", "VIN"},
    "board-esp32-devkit-c-v4": {
        "3V3", "EN", "VP", "VN", "34", "35", "32", "33", "25", "26", "27",
        "14", "12", "GND.1", "13", "D2", "D3", "CMD", "5V", "GND.2", "23",
        "22", "TX", "RX", "21", "GND.3", "19", "18", "5", "17", "16", "4",
        "0", "2", "15", "D1", "D0", "CLK",
    },
    "wokwi-led": {"A", "C"},
    "wokwi-resistor": {"1", "2"},
    "wokwi-pushbutton": {"1.l", "1.r", "2.l", "2.r"},
    "wokwi-potentiometer": {"VCC", "SIG", "GND"},
    "wokwi-hc-sr04": {"VCC", "TRIG", "ECHO", "GND"},
    "wokwi-lcd1602": {"VCC", "SDA", "SCL", "GND"},
    "wokwi-servo": {"PWM", "V+", "GND"},
    "wokwi-dht22": {"VCC", "SDA", "NC", "GND"},
    "wokwi-mpu6050": {"VCC", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"},
    "wokwi-buzzer": {"1", "2"},
}
FIELDS = {"id", "board", "category", "root_cause", "fix", "wokwi_visible", "how_to_see_it"}

def main():
    folders = sorted((ROOT / "circuits").iterdir())
    assert len(folders) == 20
    assert [p.name[:2] for p in folders] == [f"{i:02}" for i in range(1, 21)]
    paths = [p / "diagram.json" for p in folders]
    paths += [ROOT / "dev_answers.json", ROOT / "test_answers.json"]
    for p in paths:
        subprocess.run([sys.executable, "-c", "import json,sys; json.load(open(sys.argv[1]))", str(p)], check=True)
    print("PASS: exact json.load parse command succeeded for all 22 JSON files")
    for folder in folders:
        sketch = (folder / "sketch.ino").read_text()
        assert len(sketch.splitlines()) <= 60, folder.name
        symptom = (folder / "symptom.md").read_text().strip()
        assert symptom and not symptom.startswith("#"), folder.name
        diagram = json.loads((folder / "diagram.json").read_text())
        assert diagram["version"] == 1
        parts = {p["id"]: p for p in diagram["parts"]}
        assert len(parts) == len(diagram["parts"])
        for p in parts.values():
            assert p["type"] in PINS, (folder.name, p["type"])
            if p["type"] == "wokwi-lcd1602":
                assert p["attrs"]["pins"] == "i2c"
        for connection in diagram["connections"]:
            assert len(connection) == 4 and isinstance(connection[3], list)
            for endpoint in connection[:2]:
                part, pin = endpoint.split(":")
                if part == "$serialMonitor":
                    assert pin in {"RX", "TX"}
                else:
                    assert part in parts and pin in PINS[parts[part]["type"]], (folder.name, endpoint)
        for header, library in [("LiquidCrystal_I2C.h", "LiquidCrystal I2C"), ("Servo.h", "Servo"), ("DHT.h", "DHT sensor library")]:
            if header in sketch:
                assert library in (folder / "libraries.txt").read_text()
    entries = []
    for filename, expected in [("dev_answers.json", folders[:10]), ("test_answers.json", folders[10:])]:
        answers = json.loads((ROOT / filename).read_text())
        assert len(answers) == 10
        assert [a["id"] for a in answers] == [p.name for p in expected]
        for a, folder in zip(answers, expected):
            assert set(a) == FIELDS
            assert a["board"] in {"uno", "esp32"}
            assert a["category"] in {"wiring", "code", "timing", "power", "part-specific"}
            assert type(a["wokwi_visible"]) is bool
            assert all(a[key].strip() for key in ("root_cause", "fix", "how_to_see_it"))
            diagram = json.loads((folder / "diagram.json").read_text())
            expected_board = "wokwi-arduino-uno" if a["board"] == "uno" else "board-esp32-devkit-c-v4"
            assert diagram["parts"][0]["type"] == expected_board
        entries.extend(answers)
    assert len({a["root_cause"] for a in entries}) == 20
    print("PASS: 20 folders, required files, sketches <=60 lines, documented part/pin names, libraries, and disjoint 10/10 answer splits")
    counts = Counter(a["category"] for a in entries)
    print("Category counts: " + ", ".join(f"{key}={counts[key]}" for key in ["wiring", "code", "timing", "power", "part-specific"]))
    print("Not checked: firmware compilation or live Wokwi execution; one-primary-bug review is manual")

if __name__ == "__main__":
    main()
