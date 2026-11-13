# Evaluation validation

The evaluation fixtures were authored independently from embedded-system knowledge.
No `checks.py`, `tests/`, application implementation, or prompts were read.
Only files under `eval/` were created; no commit was made.

## Checks

Run `python3 eval/validate.py`. Every JSON file was parsed in a separate process with
`python3 -c "import json,sys; json.load(open(sys.argv[1]))" FILE`.

```text
PASS: exact json.load parse command succeeded for all 22 JSON files
PASS: 20 folders, required files, sketches <=60 lines, documented part/pin names, libraries, and disjoint 10/10 answer splits
Category counts: wiring=6, code=4, timing=3, power=0, part-specific=7
Not checked: firmware compilation or live Wokwi execution; one-primary-bug review is manual
```

Manual review covered one primary fault per project, expected observations, distinct root causes,
English symptoms for 01–15, Vietnamese symptoms for 16–20, and answer-key separation.
All visibility flags are expectations from documented component behavior; no live simulator
run or firmware compilation was available. No real-hardware-only case is included.

## Files created

69 files:

```text
eval/README.md
eval/VALIDATION.md
eval/circuits/01-status-lamp/diagram.json
eval/circuits/01-status-lamp/sketch.ino
eval/circuits/01-status-lamp/symptom.md
eval/circuits/02-door-button/diagram.json
eval/circuits/02-door-button/sketch.ino
eval/circuits/02-door-button/symptom.md
eval/circuits/03-desk-light/diagram.json
eval/circuits/03-desk-light/sketch.ino
eval/circuits/03-desk-light/symptom.md
eval/circuits/04-parking-distance/diagram.json
eval/circuits/04-parking-distance/sketch.ino
eval/circuits/04-parking-distance/symptom.md
eval/circuits/05-welcome-display/diagram.json
eval/circuits/05-welcome-display/libraries.txt
eval/circuits/05-welcome-display/sketch.ino
eval/circuits/05-welcome-display/symptom.md
eval/circuits/06-knob-monitor/diagram.json
eval/circuits/06-knob-monitor/sketch.ino
eval/circuits/06-knob-monitor/symptom.md
eval/circuits/07-help-button/diagram.json
eval/circuits/07-help-button/sketch.ino
eval/circuits/07-help-button/symptom.md
eval/circuits/08-heartbeat/diagram.json
eval/circuits/08-heartbeat/sketch.ino
eval/circuits/08-heartbeat/symptom.md
eval/circuits/09-knob-percentage/diagram.json
eval/circuits/09-knob-percentage/sketch.ino
eval/circuits/09-knob-percentage/symptom.md
eval/circuits/10-toggle-lamp/diagram.json
eval/circuits/10-toggle-lamp/sketch.ino
eval/circuits/10-toggle-lamp/symptom.md
eval/circuits/11-distance-log/diagram.json
eval/circuits/11-distance-log/sketch.ino
eval/circuits/11-distance-log/symptom.md
eval/circuits/12-slow-blink/diagram.json
eval/circuits/12-slow-blink/sketch.ino
eval/circuits/12-slow-blink/symptom.md
eval/circuits/13-lab-counter/diagram.json
eval/circuits/13-lab-counter/libraries.txt
eval/circuits/13-lab-counter/sketch.ino
eval/circuits/13-lab-counter/symptom.md
eval/circuits/14-arm-indicator/diagram.json
eval/circuits/14-arm-indicator/libraries.txt
eval/circuits/14-arm-indicator/sketch.ino
eval/circuits/14-arm-indicator/symptom.md
eval/circuits/15-room-climate/diagram.json
eval/circuits/15-room-climate/libraries.txt
eval/circuits/15-room-climate/sketch.ino
eval/circuits/15-room-climate/symptom.md
eval/circuits/16-den-ban/diagram.json
eval/circuits/16-den-ban/sketch.ino
eval/circuits/16-den-ban/symptom.md
eval/circuits/17-nut-van/diagram.json
eval/circuits/17-nut-van/sketch.ino
eval/circuits/17-nut-van/symptom.md
eval/circuits/18-cam-bien-nghieng/diagram.json
eval/circuits/18-cam-bien-nghieng/sketch.ino
eval/circuits/18-cam-bien-nghieng/symptom.md
eval/circuits/19-chuong-bao/diagram.json
eval/circuits/19-chuong-bao/sketch.ino
eval/circuits/19-chuong-bao/symptom.md
eval/circuits/20-dem-lan-bam/diagram.json
eval/circuits/20-dem-lan-bam/sketch.ino
eval/circuits/20-dem-lan-bam/symptom.md
eval/dev_answers.json
eval/test_answers.json
eval/validate.py
```
