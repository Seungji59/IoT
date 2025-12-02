// === ESP32 BH1750 Publisher (FINAL_2_2.4G / 18.210.200.6) ===
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <BH1750.h>
#include <ArduinoJson.h>

// ---------- USER CONFIG ----------
#define WIFI_SSID     "FINAL_2_2.4G"
#define WIFI_PASSWORD "de3sw2aq1."
#define MQTT_HOST     "18.210.200.6"
#define MQTT_PORT     1883
#define MQTT_USER     ""
#define MQTT_PASS     ""
#define CLIENT_ID     "esp32-lux-01"

#define TOPIC_DATA    "smartpot/lux"
#define TOPIC_LWT     "smartpot/status/lux"

const unsigned long PUBLISH_MS = 5000;
const uint8_t SAMPLES = 3;        // 평균 샘플 수
// I2C 핀: 기본(ESP32 DevKit) SDA=21, SCL=22
// 다른 보드면 Wire.begin(SDA,SCL)로 바꿔주세요.
// ---------------------------------

WiFiClient wifi;
PubSubClient mqtt(wifi);
BH1750 lightMeter;
unsigned long lastPub = 0;

void wifiConnect() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[WiFi] Connecting");
  while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print("."); }
  Serial.println(" OK");
}

void mqttConnect() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  while (!mqtt.connected()) {
    Serial.print("[MQTT] Connecting...");
    // LWT 등록 (offline), 연결되면 online 발행
    if (mqtt.connect(CLIENT_ID, MQTT_USER, MQTT_PASS, TOPIC_LWT, 1, true, "offline")) {
      mqtt.publish(TOPIC_LWT, "online", true);
      Serial.println(" OK");
    } else {
      Serial.printf(" failed rc=%d\n", mqtt.state());
      delay(1500);
    }
  }
}

void setup() {
  Serial.begin(115200);
  // 필요 시 다른 핀 사용: Wire.begin(SDA, SCL);
  Wire.begin(21, 22);
  bool ok = lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
  if (!ok) { delay(1000); lightMeter.begin(); }

  wifiConnect();
  mqttConnect();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) wifiConnect();
  if (!mqtt.connected()) mqttConnect();
  mqtt.loop();

  unsigned long now = millis();
  if (now - lastPub < PUBLISH_MS) return;
  lastPub = now;

  // ---- 평균 측정 ----
  float sum = 0.0f; uint8_t cnt = 0;
  for (uint8_t i = 0; i < SAMPLES; i++) {
    float lx = lightMeter.readLightLevel(); // lux
    if (lx >= 0.0f && isfinite(lx)) { sum += lx; cnt++; }
    delay(50);
  }
  if (cnt == 0) return;
  float lux = sum / cnt;

  // 시리얼 디버그
  Serial.printf("[BH1750] lux=%.2f (avg %u)\n", lux, cnt);

  // ---- MQTT 발행(JSON) ----
  StaticJsonDocument<48> doc;
  doc["lux"] = lux;

  char buf[48];
  size_t n = serializeJson(doc, buf, sizeof(buf));
  // 길이 오버로드는 uint8_t*가 필요 → 캐스팅
  mqtt.publish(TOPIC_DATA, (const uint8_t*)buf, n, false);
}
