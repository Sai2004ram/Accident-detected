#include <SoftwareSerial.h>

// 📡 GPS
SoftwareSerial gps(4, 3);

// 📍 GPS values
String latitude = "";
String longitude = "";

// Accelerometer
int xPin = A0;
int yPin = A1;
int zPin = A2;

// Buzzer
int buzzer = 9;

// Previous values
int prevX = 0, prevY = 0, prevZ = 0;

// 🔥 Shake system
int shakeEnergy = 0;
int triggerLevel = 80;

// Control
unsigned long lastTrigger = 0;
int cooldown = 5000;

// 🛑 STOP FLAG
bool triggered = false;

void setup() {
  Serial.begin(9600);
  gps.begin(9600);
  pinMode(buzzer, OUTPUT);

  Serial.println("🚀 System Started...");
}

void loop() {

  // 🛑 STOP AFTER DETECTION
  if (triggered) {
    return; // loop stop
  }

  // 🔹 Accelerometer Read
  int x = analogRead(xPin);
  int y = analogRead(yPin);
  int z = analogRead(zPin);

  // 🔹 Movement calculation
  int dx = abs(x - prevX);
  int dy = abs(y - prevY);
  int dz = abs(z - prevZ);

  int diff = dx + dy + dz;

  // 🔥 Energy logic
  if (diff > 10) {
    shakeEnergy += diff;
  } else {
    shakeEnergy -= 5;
  }

  shakeEnergy = constrain(shakeEnergy, 0, 300);

  Serial.print("Energy: ");
  Serial.println(shakeEnergy);

  // 🚨 SHAKE DETECT
  if (shakeEnergy > triggerLevel && millis() - lastTrigger > cooldown) {

    Serial.println("⚠️ Accident Detected!");
    digitalWrite(buzzer, HIGH);

    readGPS();

    if (latitude != "" && longitude != "") {
      Serial.print("📍 https://www.google.com/maps?q=");
      Serial.print(latitude);
      Serial.print(",");
      Serial.println(longitude);
    } else {
      Serial.println("❌ GPS NOT FIXED");
    }

    // 🔥 STOP SYSTEM HERE
    triggered = true;
  } 
  else {
    digitalWrite(buzzer, LOW);
  }

  prevX = x;
  prevY = y;
  prevZ = z;

  delay(150);
}


// 📡 GPS FUNCTION
void readGPS() {

  latitude = "";
  longitude = "";

  unsigned long start = millis();

  while (millis() - start < 8000) {

    while (gps.available()) {

      String line = gps.readStringUntil('\n');

      if (line.indexOf("$GPRMC") >= 0) {

        String parts[20];
        int index = 0;

        for (int i = 0; i < line.length(); i++) {
          if (line[i] == ',') {
            index++;
          } else {
            parts[index] += line[i];
          }
        }

        if (parts[2] == "A") {

          latitude = convert(parts[3], parts[4]);
          longitude = convert(parts[5], parts[6]);

          Serial.println("GPS FIXED ✅");
          return;
        }
      }
    }
  }
}


// 📍 Convert
String convert(String raw, String dir) {

  if (raw == "") return "";

  float val = raw.toFloat();

  int deg = int(val / 100);
  float min = val - (deg * 100);

  float dec = deg + (min / 60);

  if (dir == "S" || dir == "W") {
    dec = -dec;
  }

  return String(dec, 6);
}