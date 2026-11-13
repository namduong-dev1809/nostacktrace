bool lampOn = false;
void setup() { pinMode(9, OUTPUT); }
void loop() {
  unsigned long previous = millis();
  while (millis() - previous < 1000) {
    delayMicroseconds(100);
  }
  lampOn = !lampOn;
  digitalWrite(9, lampOn);
  delayMicroseconds(1000);
  lampOn = !lampOn;
  digitalWrite(9, lampOn);
}
