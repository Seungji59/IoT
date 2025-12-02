// === ESP32 Soil Moisture Publisher ===
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ---------- USER CONFIG ----------
#define WIFI_SSID     "FINAL_2_2.4G"
#define WIFI_PASSWORD     "de3sw2aq1."
#define MQTT_HOST     "18.210.200.6"
#define MQTT_PORT     1883
#define MQTT_USER     ""   // 필요시
#define MQTT_PASS     ""   // 필요시
#define CLIENT_ID     "esp32-soil-01"

#define TOPIC_DATA    "smartpot/soil"
#define TOPIC_LWT     "smartpot/status/soil"

#define SOIL_PIN      34   // ADC1_CH0
const unsigned long PUBLISH_MS = 5000;
const uint8_t SAMPLES = 8;         // 아날로그 평균
// 현장 보정 필수: 건조/습윤 원시값
int RAW_DRY = 2960;                 // 공기중
int RAW_WET = 1500;                 // 물에 담갔을 때
// ---------------------------------

WiFiClient wifi;
PubSubClient mqtt(wifi);
unsigned long lastPub = 0;

void wifiConnect() 
{
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(400); }
}
void mqttConnect() 
{
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  while (!mqtt.connected()) 
  {
    mqtt.connect(CLIENT_ID, MQTT_USER, MQTT_PASS, TOPIC_LWT, 1, true, "offline");
    if (!mqtt.connected()) delay(1500);
  }
  mqtt.publish(TOPIC_LWT, "online", true);
}

float toPct(int raw) 
{
  // 선형 맵 + 클램프
  float pct = (float)(RAW_DRY - raw) * 100.0f / (RAW_DRY - RAW_WET);
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

void setup() 
{
  Serial.begin(115200);
  analogReadResolution(12);                  // 0..4095
  analogSetPinAttenuation(SOIL_PIN, ADC_11db); // 0~3.6V
  wifiConnect();
  mqttConnect();
}

void loop() 
{
  if (WiFi.status() != WL_CONNECTED) wifiConnect();
  if (!mqtt.connected()) mqttConnect();
  mqtt.loop();

  unsigned long now = millis();
  if (now - lastPub < PUBLISH_MS) return;
  lastPub = now;

  // 다중 샘플 평균
  long acc = 0;
  for (uint8_t i=0;i<SAMPLES;i++) 
  {
    acc += analogRead(SOIL_PIN);
    delay(10);
  }
  int raw = acc / SAMPLES;
  float pct = toPct(raw);

  StaticJsonDocument<48> doc;
  doc["moisture_pct"] = pct;
  char buf[64];
  size_t n = serializeJson(doc, buf, sizeof(buf));
  mqtt.publish(TOPIC_DATA, (const uint8_t*)buf, n, false);
}
