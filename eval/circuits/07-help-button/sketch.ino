void setup() {
  pinMode(23, OUTPUT);
  pinMode(18, INPUT_PULLUP);
}
void loop() {
  digitalWrite(23, digitalRead(18) == LOW);
  delay(5000);
}
