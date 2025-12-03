#include <WiFi.h>
#include <PubSubClient.h>

// ===== USER CONFIG =====
#define WIFI_SSID     "FINAL_2_2.4G"
#define WIFI_PASS     "de3sw2aq1."
#define MQTT_HOST     "18.210.200.6"
#define MQTT_PORT     1883
#define MQTT_USER     ""      // 필요시
#define MQTT_PASS     ""      // 필요시

#define CLIENT_ID     "esp32-led-01"
#define TOPIC_CMD     "smartpot/led/set"       // Node-RED function이 발행
#define TOPIC_STATUS  "smartpot/led/status"    // 현재 상태 회신
#define TOPIC_LWT     "smartpot/status/led"    // online/offline

#define RELAY_PIN     13       // 사용 핀에 맞게 변경
#define ACTIVE_HIGH   true   // true: HIGH=ON, false: LOW=ON (모듈에 맞게)
// ========================

WiFiClient wifi;
PubSubClient mqtt(wifi);
int relayState = 0; // 0=OFF, 1=ON

inline void applyRelay(int s){
  relayState = s;
  if (ACTIVE_HIGH) digitalWrite(RELAY_PIN, s ? HIGH : LOW);
  else              digitalWrite(RELAY_PIN, s ? LOW  : HIGH);
}

void wifiConnect(){
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(400); }
  Serial.println("[WiFi] connected");
}

void onMsg(char* topic, byte* payload, unsigned int len){
  String cmd; cmd.reserve(len);
  for (unsigned int i=0;i<len;i++) cmd += (char)payload[i];
  cmd.trim();
  Serial.printf("[MQTT] %s -> %s\n", topic, cmd.c_str());

  if (cmd == "1") { applyRelay(1); mqtt.publish(TOPIC_STATUS, "1", true); }
  else if (cmd == "0") { applyRelay(0); mqtt.publish(TOPIC_STATUS, "0", true); }
  // 그 외 값은 무시
}

void mqttConnect(){
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMsg);
  mqtt.setKeepAlive(30);
  mqtt.setSocketTimeout(30);

  while (!mqtt.connected()){
    if (mqtt.connect(CLIENT_ID, MQTT_USER, MQTT_PASS, TOPIC_LWT, 1, true, "offline")){
      mqtt.publish(TOPIC_LWT, "online", true);     // retained
      mqtt.subscribe(TOPIC_CMD, 1);                // QoS1
      mqtt.publish(TOPIC_STATUS, relayState ? "1":"0", true);
      Serial.println("[MQTT] connected");
    } else {
      delay(1500);
    }
  }
}

void setup(){
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  applyRelay(0);           // 부팅 기본 OFF
  wifiConnect();
  mqttConnect();
}

void loop(){
  if (WiFi.status() != WL_CONNECTED) wifiConnect();
  if (!mqtt.connected()) mqttConnect();
  mqtt.loop();
}
