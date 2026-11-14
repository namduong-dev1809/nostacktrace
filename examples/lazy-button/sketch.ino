// Lab: a status LED blinks, and the button toggles the lamp.
#define BUTTON 2
#define LAMP 8
#define STATUS 13

bool lampOn = false;

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON, INPUT_PULLUP);
  pinMode(LAMP, OUTPUT);
  pinMode(STATUS, OUTPUT);
}

void loop() {
  digitalWrite(STATUS, HIGH);
  delay(1000);
  digitalWrite(STATUS, LOW);
  delay(1000);

  if (digitalRead(BUTTON) == LOW) {
    lampOn = !lampOn;
    digitalWrite(LAMP, lampOn);
    Serial.println(lampOn ? "lamp ON" : "lamp OFF");
  }
}
