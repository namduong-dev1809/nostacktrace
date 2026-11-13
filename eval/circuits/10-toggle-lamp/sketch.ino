bool lampOn = false;
void setup() {
  pinMode(23, OUTPUT);
  pinMode(18, INPUT_PULLUP);
}
void loop() {
  if (digitalRead(18) == LOW) {
    lampOn = !lampOn;
    digitalWrite(23, lampOn);
  }
  delay(100);
}
