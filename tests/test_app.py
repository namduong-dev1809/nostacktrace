import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app  # noqa: E402
import diagnose  # noqa: E402

EX = Path(__file__).parent.parent / "examples" / "maze-sonar"
SKETCH, DIAGRAM = (EX / "sketch.ino").read_text(), (EX / "diagram.json").read_text()


class TestRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = app.CACHE, app.diagnose
        app.CACHE = Path(self.tmp.name)

    def tearDown(self):
        app.CACHE, app.diagnose = self.orig
        self.tmp.cleanup()

    def go(self, diagram=DIAGRAM, log=""):
        return app.run(SKETCH, diagram, "", "it freezes", "English", "wokwi", log)

    def test_model_failure_is_not_blamed_on_diagram(self):
        def boom(*a):
            raise RuntimeError("all models failed (gemini-x: JSONDecodeError)")
        app.diagnose = boom
        out = self.go()
        self.assertIn("AI explanation unavailable", out)
        self.assertNotIn("diagram.json", out)
        self.assertIn("pulseIn", out)  # code-check findings still shown
        self.assertEqual(list(app.CACHE.iterdir()), [])  # failures are not cached

    def test_malformed_diagram(self):
        for bad in ("[]", '{"parts": [{"id": "x"}]}', '{"parts": [], "connections": [["a"]]}', "{"):
            self.assertIn("not a valid Wokwi diagram", self.go(bad), bad)
        self.assertIn("no Arduino Uno or ESP32", self.go('{"parts": [{"id": "n", "type": "wokwi-arduino-nano"}]}'))

    def test_input_too_long(self):
        self.assertIn("too long", app.run("x" * 30_000, DIAGRAM, "", "s", "English", "wokwi"))

    def test_bad_model_answer_moves_to_next_model(self):
        answers = iter(['{"summary": "x"}', json.dumps({"summary": "ok", "causes": [dict(
            title="t", category="code", likelihood="high", why="w", check="c", fix="f", source="reasoning")]})])
        orig = diagnose.generate
        diagnose.generate = lambda *a, **k: next(answers)
        try:
            result, model = diagnose.generate_any("p", models=["m1", "m2"], parse=diagnose.parse_result)
        finally:
            diagnose.generate = orig
        self.assertEqual((result["summary"], model), ("ok", "m2"))

    def test_corrupt_cache_file_is_a_miss(self):
        calls = []
        app.diagnose = lambda *a: calls.append(1) or {"summary": "fresh", "causes": [], "rule_findings": [], "model": "m"}
        self.go()
        (cached,) = app.CACHE.iterdir()
        cached.write_text("{half")
        self.assertIn("fresh", self.go())
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
