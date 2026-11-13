# NoStackTrace circuit evaluation set

Twenty independent beginner debugging projects for Wokwi. Each project contains one primary fault.
Circuits 01–10 are the development split; circuits 11–20 are held out.
Do not expose either answer file to the assistant being evaluated. Load only the selected
project's sketch, diagram, and symptom during evaluation.

## Running a project

Create a new Arduino Uno or ESP32 DevKitC V4 project in Wokwi matching the board below.
Copy `sketch.ino` and `diagram.json`; also copy `libraries.txt` when present, or install its
listed libraries with Wokwi's Library Manager. Start simulation and follow `symptom.md`.
ESP32 diagrams include the serial monitor UART connections. All sketches use 115200 baud
when serial output is present. Button bounce is disabled so it cannot introduce a second fault.
Enable simulator audio when testing projects that use a buzzer.

`dev_answers.json` contains the development answer key. `test_answers.json` is the held-out
answer key and must remain separate from prompts, reports, and public circuit descriptions.
The `wokwi_visible` field describes expected simulator behavior, not a recorded simulator run.

## Inventory

| ID | Board | Parts |
| --- | --- | --- |
| 01-status-lamp | Arduino Uno | led, resistor |
| 02-door-button | ESP32 DevKitC V4 | pushbutton |
| 03-desk-light | Arduino Uno | led, resistor |
| 04-parking-distance | Arduino Uno | hc-sr04 |
| 05-welcome-display | Arduino Uno | lcd1602 |
| 06-knob-monitor | ESP32 DevKitC V4 | potentiometer |
| 07-help-button | ESP32 DevKitC V4 | led, resistor, pushbutton |
| 08-heartbeat | Arduino Uno | led, resistor |
| 09-knob-percentage | Arduino Uno | potentiometer |
| 10-toggle-lamp | ESP32 DevKitC V4 | led, resistor, pushbutton |
| 11-distance-log | Arduino Uno | hc-sr04 |
| 12-slow-blink | Arduino Uno | led, resistor |
| 13-lab-counter | Arduino Uno | lcd1602 |
| 14-arm-indicator | Arduino Uno | led, resistor, servo |
| 15-room-climate | Arduino Uno | dht22, resistor |
| 16-den-ban | Arduino Uno | led, resistor |
| 17-nut-van | ESP32 DevKitC V4 | potentiometer |
| 18-cam-bien-nghieng | ESP32 DevKitC V4 | mpu6050 |
| 19-chuong-bao | Arduino Uno | buzzer |
| 20-dem-lan-bam | Arduino Uno | pushbutton |

## Part references

Pin names and part types were checked against the official Wokwi documentation source.
The website returned HTTP 403 in this environment, so its official source was used:
[Wokwi documentation](https://github.com/wokwi/wokwi-docs/tree/main/docs/parts).

- [Arduino Uno](https://docs.wokwi.com/parts/wokwi-arduino-uno)
- [ESP32 simulation](https://docs.wokwi.com/guides/esp32) and
  [DevKitC V4 board pin definition](https://github.com/wokwi/wokwi-boards/blob/main/boards/esp32-devkit-c-v4/board.json)
- [LED](https://docs.wokwi.com/parts/wokwi-led)
- [Resistor](https://docs.wokwi.com/parts/wokwi-resistor)
- [Pushbutton](https://docs.wokwi.com/parts/wokwi-pushbutton)
- [Potentiometer](https://docs.wokwi.com/parts/wokwi-potentiometer)
- [HC-SR04](https://docs.wokwi.com/parts/wokwi-hc-sr04)
- [LCD1602](https://docs.wokwi.com/parts/wokwi-lcd1602)
- [Servo](https://docs.wokwi.com/parts/wokwi-servo)
- [DHT22](https://docs.wokwi.com/parts/wokwi-dht22)
- [MPU6050](https://docs.wokwi.com/parts/wokwi-mpu6050)
- [Buzzer](https://docs.wokwi.com/parts/wokwi-buzzer)
