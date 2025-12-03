#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <time.h>

// ===== 하드웨어 설정 =====
#define DHTPIN   13          // DHT22 데이터 핀 (필요시 4/5 등으로 변경)
#define DHTTYPE  DHT22
DHT dht(DHTPIN, DHTTYPE);

// ===== 네트워크 / MQTT =====
const char* WIFI_SSID   = "FINAL_2_2.4G";
const char* WIFI_PASS   = "de3sw2aq1.";
const char* MQTT_SERVER = "18.210.200.6";
const int   MQTT_PORT   = 1883;

// 발행 토픽 (Node-RED Function 9과 일치)
const char* PUB_TOPIC = "smartpot/temp_humi";
const char* DEVICE_ID = "temp_humi_sensor_01";

// 발행 주기(ms)
const unsigned long PUB_INTERVAL_MS = 5 * 1000;

WiFiClient espClient;
PubSubClient mqtt(espClient);
unsigned long lastPub = 0;

// ===== ISO8601(+09:00) 문자열 =====
String iso8601() {
  time_t now = time(nullptr);
  struct tm tm_info;
  localtime_r(&now, &tm_info);
  char buf[32];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S%z", &tm_info); // ...+0900
  String s(buf);
  if (s.length() >= 5) s = s.substring(0, s.length()-2) + ":" + s.substring(s.length()-2); // → +09:00
  return s;
}

// ===== Wi-Fi 연결 =====
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) { Serial.print("."); delay(300); }
  Serial.print("\nWiFi OK, IP="); Serial.println(WiFi.localIP());

  // NTP (KST +09:00)
  configTime(9 * 3600, 0, "pool.ntp.org", "time.google.com");
  for (int i=0; i<50; i++) { if (time(nullptr) > 1700000000) break; delay(100); }
}

// ===== MQTT 연결 =====
void ensureMqtt() {
  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setKeepAlive(60);
  mqtt.setSocketTimeout(30);

  while (!mqtt.connected()) {
    String cid = String(DEVICE_ID) + "_" + String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.print("MQTT connect...");
    if (mqtt.connect(cid.c_str())) {
      Serial.println("OK");
      // 필요시 LWT/상태토픽 설정 가능
      // mqtt.connect(cid.c_str(), willTopic, willQos, willRetain, willMessage);
    } else {
      Serial.print("FAIL rc="); Serial.println(mqtt.state());
      delay(1000);
    }
  }
}

// ===== DHT22 안정 읽기(재시도 + 범위검증) =====
bool readDHT(float &t, float &h) {
  for (int i=0; i<3; i++) {
    t = dht.readTemperature();   // °C
    h = dht.readHumidity();      // %RH
    if (!isnan(t) && !isnan(h) && t>-20 && t<80 && h>=0 && h<=100) return true;
    delay(2000); // DHT22 권장 최소 간격
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  pinMode(DHTPIN, INPUT_PULLUP); // 모듈형이면 무시돼도 무방
  dht.begin();

  connectWiFi();

  // 워밍업: 초기 2회 버림(센서 안정화)
  delay(2000); dht.readTemperature(); dht.readHumidity();
  delay(2000); dht.readTemperature(); dht.readHumidity();
}

void loop() {
  if (!mqtt.connected()) ensureMqtt();
  mqtt.loop();

  if (millis() - lastPub < PUB_INTERVAL_MS) return;
  lastPub = millis();

  float t, h;
  if (!readDHT(t, h)) {
    Serial.println("DHT read bad/NaN -> skip");
    return;
  }

  // === JSON 생성 (Node-RED Function 9이 기대하는 키 이름) ===
  StaticJsonDocument<200> doc;
  doc["device"] = DEVICE_ID;
  doc["ts"] = iso8601();    // "YYYY-MM-DDTHH:MM:SS+09:00"
  doc["temperature"] = t;   // ★ temperature
  doc["humidity"] = h;      // ★ humidity (DB에서는 external_humidity로 매핑)

  char payload[200];
  size_t n = serializeJson(doc, payload, sizeof(payload));

  // 센서 값은 retain=false 권장 (재시작 시 중복 INSERT 방지)
  bool ok = mqtt.publish(PUB_TOPIC, (const uint8_t*)payload, (unsigned int)n, false);
  Serial.print("PUB "); Serial.print(ok ? "OK " : "FAIL "); Serial.println(payload);
}
