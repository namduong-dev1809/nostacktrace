#include <Wire.h>
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2);
unsigned long count = 0;
void setup() {
  lcd.init();
  lcd.backlight();
}
void loop() {
  lcd.setCursor(0, 0);
  lcd.print("Count: ");
  lcd.print(count++);
  lcd.clear();
  delay(1000);
}
