// Lab: show a counter on a 16x2 I2C LCD.
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x3F, 16, 2);
int count = 0;

void setup() {
  Serial.begin(115200);
  lcd.init();
  lcd.backlight();
  lcd.print("Hello lab!");
}

void loop() {
  lcd.setCursor(0, 1);
  lcd.print(count++);
  delay(500);
}
