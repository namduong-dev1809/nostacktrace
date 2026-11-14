// Lab: show a counter on a 16x2 I2C LCD.
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Arduino.h>

// ---- NoStackTrace trace header (generated; remove when done) ----
struct NstEv { unsigned long t, v, took; int line; char kind; int pin; };
static NstEv nst_buf[24];
static int nst_n;
static unsigned long nst_hits[64], nst_dropped;
static bool nst_want(int line) {
  unsigned long n = ++nst_hits[line & 63];
  return n <= 3 || (n & (n - 1)) == 0;
}
static void nst_add(int line, char kind, int pin, unsigned long v, unsigned long took) {
  if (nst_n < 24) nst_buf[nst_n++] = NstEv{millis(), v, took, line, kind, pin};
  else nst_dropped++;
}
static void nst_flush() {
  for (int i = 0; i < nst_n; i++) {
    NstEv &e = nst_buf[i];
    Serial.print(F("NST|t=")); Serial.print(e.t); Serial.print(F("|L")); Serial.print(e.line); Serial.print('|');
    if (e.kind == 'w') { Serial.print(F("digitalWrite(")); Serial.print(e.pin); Serial.print(','); Serial.print(e.v); Serial.println(')'); continue; }
    if (e.kind == 'm') { Serial.print(F("pinMode(")); Serial.print(e.pin); Serial.print(','); Serial.print(e.v); Serial.println(')'); continue; }
    Serial.print(e.kind == 'r' ? F("digitalRead(") : e.kind == 'a' ? F("analogRead(") : F("pulseIn("));
    Serial.print(e.pin); Serial.print(F(")=")); Serial.print(e.v);
    if (e.kind == 'p') { Serial.print(F("|took_us=")); Serial.print(e.took); }
    Serial.println();
  }
  nst_n = 0;
  if (nst_dropped) { Serial.print(F("NST|dropped=")); Serial.println(nst_dropped); nst_dropped = 0; }
}
static int nst_dr(int pin, int line) {
  int v = (digitalRead)(pin);
  if (nst_want(line)) nst_add(line, 'r', pin, v, 0);
  return v;
}
static void nst_dw(int pin, int val, int line) {
  (digitalWrite)(pin, val);
  if (nst_want(line)) nst_add(line, 'w', pin, val, 0);
}
static int nst_ar(int pin, int line) {
  int v = (analogRead)(pin);
  if (nst_want(line)) nst_add(line, 'a', pin, v, 0);
  return v;
}
static void nst_pm(int pin, int mode, int line) {
  (pinMode)(pin, mode);
  nst_add(line, 'm', pin, mode, 0);
}
static unsigned long nst_pi_core(int line, int pin, int state, unsigned long timeout, bool given) {
  unsigned long t0 = micros();
  unsigned long v = given ? (pulseIn)(pin, state, timeout) : (pulseIn)(pin, state);
  unsigned long dt = micros() - t0;
  if (dt > 100000UL || nst_want(line)) nst_add(line, 'p', pin, v, dt);
  return v;
}
static unsigned long nst_pi(int line, int pin, int state, int) { return nst_pi_core(line, pin, state, 0, false); }
static unsigned long nst_pi(int line, int pin, int state, unsigned long timeout, int) { return nst_pi_core(line, pin, state, timeout, true); }
#define digitalRead(p) nst_dr((p), __LINE__)
#define digitalWrite(p, v) nst_dw((p), (v), __LINE__)
#define analogRead(p) nst_ar((p), __LINE__)
#define pinMode(p, m) nst_pm((p), (m), __LINE__)
#define pulseIn(...) nst_pi(__LINE__, __VA_ARGS__, 0)
#define setup nst_user_setup
#define loop nst_user_loop
// ---- end of trace header ----

#line 4

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

// ---- NoStackTrace trace footer (generated) ----
#undef setup
#undef loop
static unsigned long nst_loops, nst_slowest;
void setup() {
  Serial.begin(115200);
  delay(50);
  Serial.println(F("NST|start|board=uno"));
  Wire.begin();
  Serial.print(F("NST|i2c_scan="));
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) { Serial.print(F("0x")); Serial.print(a, HEX); Serial.print(' '); }
  }
  Serial.println();
  nst_user_setup();
  nst_flush();
  Serial.println(F("NST|setup_done"));
}
void loop() {
  unsigned long t0 = micros();
  nst_user_loop();
  unsigned long dt = micros() - t0;
  nst_flush();
  nst_loops++;
  if (dt > nst_slowest) {
    nst_slowest = dt;
    Serial.print(F("NST|t=")); Serial.print(millis()); Serial.print(F("|loop_slowest_us=")); Serial.print(dt);
    Serial.print(F("|loops=")); Serial.println(nst_loops);
  }
}
