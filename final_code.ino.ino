// ============================================================
//  Smart Accident Detection — FINAL VERSION
//  Sensors : Analog Accelerometer (A0,A1,A2) + GPS + Buzzer
//  Output  : JSON → Python Dashboard via Serial
// ============================================================

#include <SoftwareSerial.h>

SoftwareSerial gps(4, 3);  // GPS TX→4, RX→3

// Pins
int xPin   = A0;
int yPin   = A1;
int zPin   = A2;
int buzzer = 9;

// GPS
String latitude  = "";
String longitude = "";

// Shake detection
int prevX = 0, prevY = 0, prevZ = 0;
int shakeEnergy  = 0;
int triggerLevel = 80;

// Control
unsigned long lastTrigger = 0;
int cooldown   = 5000;
bool triggered = false;

// ============================================================
void setup() {
  Serial.begin(9600);
  gps.begin(9600);
  pinMode(buzzer, OUTPUT);
  digitalWrite(buzzer, LOW);

  // Tell dashboard system is ready
  Serial.println("{\"type\":\"STATUS\",\"msg\":\"READY\"}");
}

// ============================================================
void loop() {

  // Read accelerometer
  int x = analogRead(xPin);
  int y = analogRead(yPin);
  int z = analogRead(zPin);

  int dx   = abs(x - prevX);
  int dy   = abs(y - prevY);
  int dz   = abs(z - prevZ);
  int diff = dx + dy + dz;

  // Shake energy
  if (diff > 10) shakeEnergy += diff;
  else           shakeEnergy -= 5;
  shakeEnergy = constrain(shakeEnergy, 0, 300);

  // Send live JSON every loop
  Serial.print("{\"type\":\"LIVE\"");
  Serial.print(",\"x\":"); Serial.print(x);
  Serial.print(",\"y\":"); Serial.print(y);
  Serial.print(",\"z\":"); Serial.print(z);
  Serial.print(",\"energy\":"); Serial.print(shakeEnergy);
  Serial.print(",\"triggered\":"); Serial.print(triggered ? "true" : "false");
  Serial.println("}");

  // Accident detect
  if (!triggered &&
      shakeEnergy > triggerLevel &&
      millis() - lastTrigger > cooldown) {

    lastTrigger = millis();
    triggered   = true;

    // Buzzer ON
    for (int i = 0; i < 5; i++) {
      digitalWrite(buzzer, HIGH); delay(300);
      digitalWrite(buzzer, LOW);  delay(200);
    }

    // Read GPS
    readGPS();

    // Send accident JSON
    Serial.print("{\"type\":\"ACCIDENT\"");
    Serial.print(",\"energy\":"); Serial.print(shakeEnergy);
    Serial.print(",\"lat\":\""); Serial.print(latitude);  Serial.print("\"");
    Serial.print(",\"lon\":\""); Serial.print(longitude); Serial.print("\"");
    Serial.print(",\"gps_fixed\":"); Serial.print(latitude != "" ? "true" : "false");
    Serial.println("}");
  }

  prevX = x;
  prevY = y;
  prevZ = z;

  delay(150);
}

// ============================================================
void readGPS() {
  latitude  = "";
  longitude = "";

  unsigned long start = millis();
  while (millis() - start < 8000) {
    while (gps.available()) {
      String line = gps.readStringUntil('\n');
      if (line.indexOf("$GPRMC") >= 0) {
        String parts[20];
        int idx = 0;
        for (int i = 0; i < (int)line.length(); i++) {
          if (line[i] == ',') idx++;
          else parts[idx] += line[i];
        }
        if (parts[2] == "A") {
          latitude  = convertGPS(parts[3], parts[4]);
          longitude = convertGPS(parts[5], parts[6]);
          Serial.println("{\"type\":\"STATUS\",\"msg\":\"GPS_FIXED\"}");
          return;
        }
      }
    }
  }
  Serial.println("{\"type\":\"STATUS\",\"msg\":\"GPS_NO_FIX\"}");
}

String convertGPS(String raw, String dir) {
  if (raw == "") return "";
  float val = raw.toFloat();
  int   deg = int(val / 100);
  float mn  = val - (deg * 100);
  float dec = deg + (mn / 60.0);
  if (dir == "S" || dir == "W") dec = -dec;
  return String(dec, 6);
}

