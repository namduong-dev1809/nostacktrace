void setup() { pinMode(4, OUTPUT); }
void loop() {
  for (int brightness = 0; brightness <= 255; brightness++) {
    analogWrite(4, brightness);
    delay(20);
  }
}
