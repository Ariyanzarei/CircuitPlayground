// Samples the KY-038 microphone at 8 kHz and streams raw samples over WiFi as UDP packets.
//
// Two jobs run in parallel on the ESP32's two CPU cores:
//   core 1 (loop):        read the ADC exactly every 125 us -> fill a 256-sample buffer
//   core 0 (senderTask):  take full buffers from a queue -> send each as one UDP packet
// Splitting them means WiFi sending never delays sampling (which would cause clicks).
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include "secrets.h"

const int MIC_PIN = 34;                   // must be an ADC1 pin: ADC2 is unusable while WiFi is on
const uint32_t SAMPLE_RATE = 8000;        // 8 kHz = phone quality, enough for voice
const uint32_t PERIOD_US = 1000000 / SAMPLE_RATE;
const int SAMPLES_PER_PACKET = 256;       // 32 ms of audio, 512 bytes
const uint16_t UDP_PORT = 4211;
// Broadcast = every device on your LAN receives it. If audio is choppy, use your PC's IP instead.
const IPAddress TARGET(255, 255, 255, 255);

QueueHandle_t packets;                    // hands full buffers from core 1 to core 0

void senderTask(void *) {
  WiFiUDP udp;
  uint16_t buf[SAMPLES_PER_PACKET];
  uint32_t seq = 0;   // packet counter: lets the PC drop duplicates (e.g. PC on WiFi + Ethernet)
  while (true) {
    xQueueReceive(packets, buf, portMAX_DELAY);   // sleep until a buffer is ready
    seq++;
    udp.beginPacket(TARGET, UDP_PORT);
    udp.write((uint8_t *)&seq, sizeof(seq));      // 4-byte header
    udp.write((uint8_t *)buf, sizeof(buf));       // raw 12-bit values as uint16 (little-endian)
    udp.endPacket();
  }
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);               // values 0..4095
  analogSetPinAttenuation(MIC_PIN, ADC_11db);  // input range ~0..3.1 V

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);                   // power-save adds big latency spikes
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (WiFi.status() == WL_NO_SSID_AVAIL) Serial.printf("\nNetwork \"%s\" not found - check secrets.h\n", WIFI_SSID);
  }
  Serial.printf("\nConnected, ESP32 IP: %s\n", WiFi.localIP().toString().c_str());

  packets = xQueueCreate(4, sizeof(uint16_t) * SAMPLES_PER_PACKET);
  xTaskCreatePinnedToCore(senderTask, "sender", 4096, nullptr, 1, nullptr, 0);
}

void loop() {
  static uint16_t buf[SAMPLES_PER_PACKET];
  static int n = 0;
  static uint32_t next = micros();
  static uint32_t lastPrint = 0;

  while ((int32_t)(micros() - next) < 0) {}   // busy-wait for precise timing
  next += PERIOD_US;

  buf[n++] = analogRead(MIC_PIN);
  if (n == SAMPLES_PER_PACKET) {
    xQueueSend(packets, buf, 0);          // copy into queue; drop if the sender is behind
    n = 0;
    if (millis() - lastPrint > 1000) {    // once a second: show the raw level (debug aid)
      Serial.printf("sample: %u\n", buf[0]);
      lastPrint = millis();
    }
  }
}
