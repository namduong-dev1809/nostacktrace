"""Compile every eval/example sketch, original and traced, with arduino-cli.

usage: ARDUINO_CLI=/path/to/arduino-cli python compile_check.py [name-filter]
Needs the arduino:avr and esp32:esp32 cores and the libraries the sketches include.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from checks import Diagram
from nst_trace import instrument

ROOT = Path(__file__).parent
CLI = os.environ.get("ARDUINO_CLI", "arduino-cli")
FQBN = {"uno": "arduino:avr:uno", "esp32": "esp32:esp32:esp32"}


def compile_sketch(code, fqbn, name):
    with tempfile.TemporaryDirectory() as d:
        sk = Path(d) / name
        sk.mkdir()
        (sk / f"{name}.ino").write_text(code)
        r = subprocess.run([CLI, "compile", "--fqbn", fqbn, str(sk)], capture_output=True, text=True)
        err = [l for l in (r.stdout + r.stderr).splitlines() if "error" in l.lower()]
        return r.returncode == 0, err[:3]


def main(filt=""):
    dirs = sorted((ROOT / "eval" / "circuits").iterdir()) + sorted((ROOT / "examples").iterdir())
    bad = 0
    for c in dirs:
        if filt not in c.name:
            continue
        board = Diagram((c / "diagram.json").read_text()).board
        code = (c / "sketch.ino").read_text()
        name = c.name.replace("-", "_")
        ok_orig, err_orig = compile_sketch(code, FQBN[board], name)
        ok_tr, err_tr = compile_sketch(instrument(code, board)[0], FQBN[board], name)
        bad += ok_orig and not ok_tr
        print(f"{c.name:24s} {board:5s} original={'ok' if ok_orig else 'FAIL'} traced={'ok' if ok_tr else 'FAIL'}", flush=True)
        for e in (err_tr if ok_orig and not ok_tr else err_orig if not ok_orig else []):
            print("    ", e[:220], flush=True)
    print("traced build broke an original that compiled:", bad)
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1] if len(sys.argv) > 1 else "") else 0)
