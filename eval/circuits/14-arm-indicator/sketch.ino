#include <Servo.h>
Servo arm;
void setup() {
  pinMode(10, OUTPUT);
  arm.attach(9);
  arm.write(90);
  analogWrite(10, 128);
}
void loop() { }
