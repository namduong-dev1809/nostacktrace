#include <DHT.h>
DHT sensor(2, DHT11);
void setup() {
  Serial.begin(115200);
  sensor.begin();
}
void loop() {
  float t = sensor.readTemperature();
  float h = sensor.readHumidity();
  if (isnan(t) || isnan(h)) Serial.println("Read failed");
  else {
    Serial.print("Temperature: ");
    Serial.print(t);
    Serial.print(" C, humidity: ");
    Serial.println(h);
  }
  delay(2500);
}
