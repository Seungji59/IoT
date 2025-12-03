#include <WiFi.h>
#include <PubSubClient.h>

// ===== USER CONFIG =====
#define WIFI_SSID     "FINAL_2_2.4G"
#define WIFI_PASS     "de3sw2aq1."
#define MQTT_HOST     "18.210.200.6"
#define MQTT_PORT     1883
#define MQTT_USER     ""
#define MQTT_PASS     ""

#define CLIENT_ID     "esp32-pump-01"
#define TOPIC_CMD     "smartpot/pump/set"
#define TOPIC_STATUS  "smartpot/pump/status"
#define TOPIC_LWT     "smartpot/status/pump"

#define RELAY_PIN     13
#define ACTIVE_HIGH   false   // Active-Low 릴레이면 false
// ========================

WiFiClient wifi;
PubSubClient mqtt(wifi);
int relayState = 0; // 0=OFF, 1=ON

inline void applyRelay(int s){
  relayState = s;
  if (ACTIVE_HIGH) digitalWrite(RELAY_PIN, s ? LOW : HIGH);
  else              digitalWrite(RELAY_PIN, s ? HIGH  : LOW);
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
}

void mqttConnect(){
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMsg);
  mqtt.setKeepAlive(30);
  mqtt.setSocketTimeout(30);

  while (!mqtt.connected()){
    if (mqtt.connect(CLIENT_ID, MQTT_USER, MQTT_PASS, TOPIC_LWT, 1, true, "offline")){
      mqtt.publish(TOPIC_LWT, "online", true);
      mqtt.subscribe(TOPIC_CMD, 1);                     // QoS1
      mqtt.publish(TOPIC_STATUS, relayState?"1":"0", true);
      Serial.println("[MQTT] connected");
    } else {
      delay(1500);
    }
  }
}

void setup(){
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  applyRelay(0); // 부팅 기본 OFF
  wifiConnect();
  mqttConnect();
}

void loop(){
  if (WiFi.status() != WL_CONNECTED) wifiConnect();
  if (!mqtt.connected()) mqttConnect();
  mqtt.loop();
}
