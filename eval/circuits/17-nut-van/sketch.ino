void setup() { Serial.begin(115200); }
void loop() {
  int raw = analogRead(34);
  float percent = raw * 100.0 / 1023.0;
  Serial.print("Muc: ");
  Serial.println(percent);
  delay(200);
}
