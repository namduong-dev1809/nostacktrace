const int buttonPin = 18;
void setup() {
  Serial.begin(115200);
  pinMode(buttonPin, INPUT_PULLUP);
}
void loop() {
  Serial.println(digitalRead(buttonPin) == LOW ? "Door open" : "Door shut");
  delay(200);
}
