unsigned long lastBlink = 0;
bool lit = false;
void setup() { pinMode(9, OUTPUT); }
void loop() {
  lastBlink = millis();
  if (millis() - lastBlink >= 500) {
    lit = !lit;
    digitalWrite(9, lit);
    lastBlink = millis();
  }
}
