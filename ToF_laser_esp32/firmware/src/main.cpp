// Reads distance from a VL53L0X over I2C and broadcasts it over WiFi as UDP packets.
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <VL53L0X.h>
#include "secrets.h"

const int SDA_PIN = 21;           // ESP32 default I2C pins
const int SCL_PIN = 22;
const uint16_t UDP_PORT = 4210;   // PC listens on this port
// Broadcast = every device on your LAN receives it, so we don't need to know the PC's IP.
// To target only your PC, use e.g. IPAddress TARGET(10, 0, 0, 242);
const IPAddress TARGET(255, 255, 255, 255);

VL53L0X sensor;
WiFiUDP udp;

void setup() {
  Serial.begin(115200);

  // 1) Sensor
  Wire.begin(SDA_PIN, SCL_PIN);
  sensor.setTimeout(500);
  if (!sensor.init()) {
    Serial.println("VL53L0X not found - check wiring!");
    while (true) delay(1000);
  }
  sensor.startContinuous();       // measure back-to-back (~33 ms per reading)

  // 2) WiFi
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);           // lower latency
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.printf("\nConnected, ESP32 IP: %s\n", WiFi.localIP().toString().c_str());
}

void loop() {
  uint16_t mm = sensor.readRangeContinuousMillimeters();  // blocks until a new reading
  // >= 8000 means "nothing in range"; timeout means the sensor stopped answering.
  bool valid = !sensor.timeoutOccurred() && mm < 8000;

  char msg[64];
  snprintf(msg, sizeof(msg), "{\"mm\":%u,\"valid\":%s}", mm, valid ? "true" : "false");

  udp.beginPacket(TARGET, UDP_PORT);
  udp.print(msg);
  udp.endPacket();

  Serial.println(msg);
}
