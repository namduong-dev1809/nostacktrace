// Maze robot brain: sweep the sonar left/centre/right, steer toward the most open side.
// Motors are not simulated in Wokwi; the decision is printed to Serial.
#include <ESP32Servo.h>

#define TRIG 5
#define ECHO 18
#define SERVO_PIN 13

Servo neck;

long readCm() {
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long us = pulseIn(ECHO, HIGH);
  return us / 58;
}

long lookAt(int angle) {
  neck.write(angle);
  delay(150);
  return readCm();
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  neck.attach(SERVO_PIN);
}

void loop() {
  long left = lookAt(150);
  long front = lookAt(90);
  long right = lookAt(30);
  unsigned long t = millis();

  if (front > 20) Serial.printf("%lu ms  FORWARD  (front %ld cm)\n", t, front);
  else if (left > right) Serial.printf("%lu ms  TURN LEFT\n", t);
  else Serial.printf("%lu ms  TURN RIGHT\n", t);
}
