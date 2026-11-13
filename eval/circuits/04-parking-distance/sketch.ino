const int triggerPin = 6;
const int echoPin = 7;
void setup() {
  Serial.begin(115200);
  pinMode(triggerPin, OUTPUT);
  pinMode(echoPin, INPUT);
}
void loop() {
  digitalWrite(triggerPin, LOW);
  delayMicroseconds(2);
  digitalWrite(triggerPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(triggerPin, LOW);
  unsigned long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) Serial.println("No echo");
  else Serial.println(duration / 58.0);
  delay(100);
}
