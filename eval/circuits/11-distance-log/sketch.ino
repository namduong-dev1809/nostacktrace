void setup() {
  Serial.begin(115200);
  pinMode(6, OUTPUT);
  pinMode(7, INPUT);
}
void loop() {
  digitalWrite(6, LOW);
  delayMicroseconds(2);
  digitalWrite(6, HIGH);
  delayMicroseconds(10);
  digitalWrite(6, LOW);
  unsigned long duration = pulseIn(7, HIGH, 1000);
  if (duration == 0) Serial.println("Out of range");
  else Serial.println(duration / 58.0);
  delay(100);
}
