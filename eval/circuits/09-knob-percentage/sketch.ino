void setup() { Serial.begin(115200); }
void loop() {
  int raw = analogRead(A0);
  float percent = (raw / 1023) * 100;
  Serial.print("Percent: ");
  Serial.println(percent);
  delay(200);
}
