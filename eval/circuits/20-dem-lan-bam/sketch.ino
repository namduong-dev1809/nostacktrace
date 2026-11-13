volatile unsigned long presses = 0;
void onPress() { presses++; }
void setup() {
  Serial.begin(115200);
  pinMode(4, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(4), onPress, FALLING);
}
void loop() {
  noInterrupts();
  unsigned long snapshot = presses;
  interrupts();
  Serial.println(snapshot);
  delay(200);
}
