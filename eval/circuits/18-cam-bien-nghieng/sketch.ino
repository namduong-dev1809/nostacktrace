#include <Wire.h>
const uint8_t imuAddress = 0x68;
void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
}
void loop() {
  Wire.beginTransmission(imuAddress);
  Wire.write(0x75);
  if (Wire.endTransmission(false) != 0) {
    Serial.println("Khong tim thay cam bien");
  } else {
    Wire.requestFrom(imuAddress, (uint8_t)1);
    if (Wire.available()) {
      Serial.print("WHO_AM_I: 0x");
      Serial.println(Wire.read(), HEX);
    }
  }
  delay(1000);
}
