/*
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>

// ===== WiFi / MQTT =====
#define WIFI_SSID   "FINAL_2_2.4G"
#define WIFI_PASS   "de3sw2aq1."
#define MQTT_HOST   "18.210.200.6"
#define MQTT_PORT   1883

// IN: Flask/Android/Node-RED가 발행 (ESP32가 구독)
#define TOPIC_CMD_IN     "smartpot/display/set"
// OUT: ESP32가 상태/ACK 발행(선택)
#define TOPIC_STATUS_OUT "smartpot/display/status"

// ===== TFT =====
TFT_eSPI tft;
uint16_t C_BG, C_EYE, C_MOUTH, C_HEART, C_STROKE;

// 하트 그리기 유틸
static inline void heart(int x, int y, int r, uint16_t c) 
{
  tft.fillCircle(x - r/2, y - r/3, r/2, c);
  tft.fillCircle(x + r/2, y - r/3, r/2, c);
  tft.fillTriangle(x - r, y - r/3, x + r, y - r/3, x, y + r, c);
}

// 공통 프레임(배경 + 테두리)
static inline void drawFrame() 
{
  tft.fillScreen(C_BG);
  tft.drawRect(4, 4, 312, 162, C_STROKE);
}

// ========== 표정 함수들 ==========
// [neutral] 하늘색 / 동그란 눈 / 얇은 라운드 입 / 좌상단 하트 1개
void drawNeutral() 
{
  // 팔레트
  C_BG     = tft.color565(180, 220, 255); // 연한 하늘색
  C_EYE    = tft.color565(0, 0, 0);       // 검정
  C_MOUTH  = tft.color565(0, 0, 0);       // 검정
  C_HEART  = tft.color565(250, 115, 60);  // 주황 하트
  C_STROKE = tft.color565(0, 0, 0);       // 테두리

  drawFrame();
  heart(26, 28, 20, C_HEART);             // 좌상단 하트 1개
  tft.fillCircle(140, 78, 10, C_EYE);     // 눈(좌)
  tft.fillCircle(200, 78, 10, C_EYE);     // 눈(우)
  tft.fillRoundRect(120, 110, 90, 14, 4, C_MOUTH); // 얇은 라운드 입
  Serial.println("[DRAW] neutral");
}

// [happy] 연두색 / < > 눈 / 직사각형 입 / 좌상단 하트 2개
void drawHappy() 
{
  C_BG     = tft.color565(180, 255, 100); // 연두
  C_EYE    = tft.color565(0, 0, 0);
  C_MOUTH  = tft.color565(0, 0, 0);
  C_HEART  = tft.color565(250, 115, 60);
  C_STROKE = tft.color565(0, 0, 0);

  drawFrame();
  heart(28, 28, 20, C_HEART);
  heart(58, 28, 20, C_HEART);

  // 눈: 왼쪽 ‘<’
  tft.fillTriangle(120, 70,  95, 55, 102, 75, C_EYE);
  tft.fillTriangle(120, 70,  95, 85, 102, 65, C_EYE);
  // 눈: 오른쪽 ‘>’
  tft.fillTriangle(200, 70, 225, 55, 218, 75, C_EYE);
  tft.fillTriangle(200, 70, 225, 85, 218, 65, C_EYE);

  // 입: 직사각형
  tft.fillRect(120, 110, 80, 18, C_MOUTH);
  Serial.println("[DRAW] happy");
}

// [love] 연핑크 / 하트 눈(빨강) / 직사각형 입 / 좌상단 하트 3개
void drawLove() 
{
  C_BG     = tft.color565(255, 210, 230); // 연핑크
  C_EYE    = tft.color565(255, 0, 0);     // 하트 눈(빨강)
  C_MOUTH  = tft.color565(0, 0, 0);
  C_HEART  = tft.color565(250, 115, 60);
  C_STROKE = tft.color565(0, 0, 0);

  drawFrame();
  heart(30, 28, 20, C_HEART);
  heart(60, 28, 20, C_HEART);
  heart(90, 28, 20, C_HEART);

  // 하트 눈(좌/우)
  heart(100, 75, 22, C_EYE);
  heart(220, 75, 22, C_EYE);

  // 입: 직사각형
  tft.fillRect(130, 112, 60, 18, C_MOUTH);
  Serial.println("[DRAW] love");
}

// ===== 상태 관리 =====
enum Mood { NEUTRAL, HAPPY, LOVE };

struct 
{
  Mood current = NEUTRAL;         // 현재 상태
  Mood lastRendered = (Mood)255;  // 마지막으로 그린 상태(초기엔 다르게)
  uint32_t expireAt = 0;          // 0이면 무기한(=neutral 기본)
} state;

static const uint32_t DEFAULT_DURATION_MS = 300000UL; // 5분 기본

// 상태가 바뀐 경우에만 실제 그리기
void renderIfChanged() 
{
  if (state.current == state.lastRendered) return;
  switch (state.current) 
  {
    case NEUTRAL: drawNeutral(); break;
    case HAPPY:   drawHappy();   break;
    case LOVE:    drawLove();    break;
  }
  state.lastRendered = state.current;
}

// 문자열 → 열거형 변환 (허용 외 입력은 neutral 처리)
Mood parseMood(const char* s) 
{
  if (!s) return NEUTRAL;
  if (!strcmp(s, "happy")) return HAPPY;
  if (!strcmp(s, "love"))  return LOVE;
  return NEUTRAL;
}

// 상태 전환 + 타이머 갱신 + 렌더
void setMood(Mood m, uint32_t durationMs ) 
{
  state.current = m;
  if (durationMs == 0) 
  {
    state.expireAt = 0; // 무기한
  } 
  else 
  {
    state.expireAt = millis() + durationMs;
  }
  renderIfChanged(); // 바뀐 경우에만 1회 그리기
}

// ===== 네트워킹 =====
WiFiClient esp;
PubSubClient mqtt(esp);

void ensureWiFi() 
{
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(400); }
}

void onMsg(char* topic, byte* payload, unsigned int len) 
{
  StaticJsonDocument<192> doc;
  if (deserializeJson(doc, payload, len)) 
  {
    Serial.println("[MQTT] JSON parse err");
    return;
  }

  const char* moodStr = doc["mood"] | "neutral";
  uint32_t dur = doc["duration_ms"] | DEFAULT_DURATION_MS; // 기본 5분

  Mood m = parseMood(moodStr);
  Serial.printf("[RX] mood=%s -> %d, duration_ms=%u\n", moodStr, (int)m, dur);

  // 상태 적용(요청 즉시 반영) — neutral은 무기한, 그 외는 dur 유지
  setMood(m, (m == NEUTRAL) ? 0 : dur);

  // (선택) ACK 발행
  StaticJsonDocument<160> ack;
  ack["ok"] = true;
  ack["mood"] = (m == HAPPY ? "happy" : m == LOVE ? "love" : "neutral");
  ack["duration_ms"] = (m == NEUTRAL ? 0 : dur);
  char buf[160]; size_t n = serializeJson(ack, buf);
  mqtt.publish(TOPIC_STATUS_OUT, buf, n);
}

void ensureMqtt() 
{
  if (mqtt.connected()) return;
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMsg);
  while (!mqtt.connected()) 
  {
    if (mqtt.connect("esp32-s3-display")) 
    {
      mqtt.subscribe(TOPIC_CMD_IN); // 명령 구독
      Serial.println("[MQTT] connected & subscribed");
    } 
    else {
      delay(800);
    }
  }
}

void setup() 
{
  Serial.begin(115200);

  // --- TFT 초기화 ---
  pinMode(38, OUTPUT);
  digitalWrite(38, HIGH);   // 백라이트 ON
  tft.init();
  tft.setRotation(1);       // 320x170 가로

  // 부팅 직후 neutral로 1회 렌더(네트워크 전부터 화면 표시)
  setMood(NEUTRAL, 0);

  // 네트워크
  ensureWiFi();
  ensureMqtt();
  Serial.println("Ready. Waiting JSON on smartpot/display/set");
}

void loop() 
{
  if (WiFi.status() != WL_CONNECTED) ensureWiFi();
  if (!mqtt.connected()) ensureMqtt();
  mqtt.loop();

  // 만료되면 neutral로 자동 복귀
  if (state.expireAt != 0) 
  {
    // millis() 오버플로우 안전 비교
    if ((int32_t)(millis() - state.expireAt) >= 0) 
    {
      setMood(NEUTRAL, 0);          // 무기한 neutral
      Serial.println("[STATE] auto back to neutral");
    }
  }

  delay(5);
}*/

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>

// ===== WiFi / MQTT =====
#define WIFI_SSID   "FINAL_2_2.4G"
#define WIFI_PASS   "de3sw2aq1."
#define MQTT_HOST   "18.210.200.6"
#define MQTT_PORT   1883

// IN: Node-RED/앱이 발행(ESP32가 구독)
#define TOPIC_CMD_IN     "smartpot/display/set"
// OUT: ESP32가 상태/ACK 발행(선택)
#define TOPIC_STATUS_OUT "smartpot/display/status"

// ===== TFT =====
TFT_eSPI tft;
uint16_t C_BG, C_EYE, C_MOUTH, C_HEART, C_STROKE;

// ===== 상태 관리 =====
// 요구사항에 맞춰 값 지정: LOVE=1, HAPPY=2, NEUTRAL=3
enum Mood { LOVE = 1, HAPPY = 2, NEUTRAL = 3 };

struct {
  Mood current = NEUTRAL;      // 현재 상태
  Mood lastRendered = (Mood)0; // 마지막으로 그린 상태(센티넬 0)
  uint32_t expireAt = 0;       // 0이면 무기한(=neutral 기본)
} state;

static const uint32_t DEFAULT_DURATION_MS = 300000UL; // 5분 기본 유지

// ===== 유틸: 하트/프레임 =====
static inline void heart(int x, int y, int r, uint16_t c)
{
  tft.fillCircle(x - r/2, y - r/3, r/2, c);
  tft.fillCircle(x + r/2, y - r/3, r/2, c);
  tft.fillTriangle(x - r, y - r/3, x + r, y - r/3, x, y + r, c);
}
static inline void drawFrame()
{
  tft.fillScreen(C_BG);
  tft.drawRect(4, 4, 312, 162, C_STROKE);
}

// ===== 표정 그리기 =====
void drawNeutral()  // [neutral] 기본 상태
{
  C_BG     = tft.color565(180, 220, 255);
  C_EYE    = tft.color565(0, 0, 0);
  C_MOUTH  = tft.color565(0, 0, 0);
  C_HEART  = tft.color565(250, 115, 60);
  C_STROKE = tft.color565(0, 0, 0);

  drawFrame();
  heart(26, 28, 20, C_HEART);
  tft.fillCircle(140, 78, 10, C_EYE);
  tft.fillCircle(200, 78, 10, C_EYE);
  tft.fillRoundRect(120, 110, 90, 14, 4, C_MOUTH);
  Serial.println("[DRAW] NEUTRAL");
}
void drawHappy()   // [happy] 보통 상태
{
  C_BG     = tft.color565(180, 255, 100);
  C_EYE    = tft.color565(0, 0, 0);
  C_MOUTH  = tft.color565(0, 0, 0);
  C_HEART  = tft.color565(250, 115, 60);
  C_STROKE = tft.color565(0, 0, 0);

  drawFrame();
  heart(28, 28, 20, C_HEART);
  heart(58, 28, 20, C_HEART);

  // 눈: 왼쪽 ‘<’
  tft.fillTriangle(120, 70,  95, 55, 102, 75, C_EYE);
  tft.fillTriangle(120, 70,  95, 85, 102, 65, C_EYE);
  // 눈: 오른쪽 ‘>’
  tft.fillTriangle(200, 70, 225, 55, 218, 75, C_EYE);
  tft.fillTriangle(200, 70, 225, 85, 218, 65, C_EYE);

  tft.fillRect(120, 110, 80, 18, C_MOUTH);
  Serial.println("[DRAW] HAPPY");
}
void drawLove()    // [love] 아주좋음 상태
{
  C_BG     = tft.color565(255, 210, 230);
  C_EYE    = tft.color565(255, 0, 0);
  C_MOUTH  = tft.color565(0, 0, 0);
  C_HEART  = tft.color565(250, 115, 60);
  C_STROKE = tft.color565(0, 0, 0);

  drawFrame();
  heart(30, 28, 20, C_HEART);
  heart(60, 28, 20, C_HEART);
  heart(90, 28, 20, C_HEART);

  heart(100, 75, 22, C_EYE);
  heart(220, 75, 22, C_EYE);

  tft.fillRect(130, 112, 60, 18, C_MOUTH);
  Serial.println("[DRAW] LOVE");
}

// ===== 렌더/상태 전환 =====
void renderIfChanged()
{
  if (state.current == state.lastRendered) return;
  switch (state.current)
  {
    case NEUTRAL: drawNeutral(); break;
    case HAPPY:   drawHappy();   break;
    case LOVE:    drawLove();    break;
  }
  state.lastRendered = state.current;
}
void setMood(Mood m, uint32_t durationMs /*0이면 무기한*/)
{
  state.current = m;
  if (durationMs == 0) state.expireAt = 0;
  else                 state.expireAt = millis() + durationMs;
  renderIfChanged();
}

// ===== 네트워킹 =====
WiFiClient esp;
PubSubClient mqtt(esp);

// Wi-Fi 연결/재연결 + 로그 출력
void ensureWiFi()
{
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.printf("[WiFi] Connecting to SSID='%s' ...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  uint8_t dot = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
    if (++dot % 20 == 0) Serial.println();
  }
  Serial.println();
  Serial.printf("[WiFi] Connected. IP=%s, RSSI=%d dBm\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());
}

// MQTT 콜백: {"level":1|2|…} 수신 → 표정 전환 + 로그 출력
void onMsg(char* topic, byte* payload, unsigned int len)
{
  StaticJsonDocument<192> doc;
  if (deserializeJson(doc, payload, len))
  {
    Serial.println("[MQTT] JSON parse err");
    return;
  }

  int level = doc["level"] | 0;                          // JSON에서 level 읽기
  uint32_t dur = doc["duration_ms"] | DEFAULT_DURATION_MS;

  // ★ 받은 원본 JSON과 해석된 값 로그
  Serial.printf("[MQTT] RX topic=%s len=%u\n", topic, len);
  Serial.printf("[MQTT] RX raw : %.*s\n", len, payload);
  Serial.printf("[MQTT] RX level: %d  (dur=%u ms)\n", level, dur);

  // level → Mood 변환 (1→LOVE, 2→HAPPY, 나머지→NEUTRAL)
  Mood m;
  if (level == 1)      m = LOVE;
  else if (level == 2) m = HAPPY;
  else                 m = NEUTRAL;

  // 상태 적용
  setMood(m, (m == NEUTRAL) ? 0 : dur);

  // (선택) ACK 발행 + 로그
  StaticJsonDocument<160> ack;
  ack["ok"] = true;
  ack["level"] = level;
  ack["mood"]  = (m == LOVE ? "love" : (m == HAPPY ? "happy" : "neutral"));
  ack["duration_ms"] = (m == NEUTRAL ? 0 : dur);
  char buf[160]; size_t n = serializeJson(ack, buf);
  mqtt.publish(TOPIC_STATUS_OUT, buf, n);
  Serial.printf("[MQTT] ACK -> %s : %s\n", TOPIC_STATUS_OUT, buf);
}

// MQTT 연결/재연결 + 로그 출력
void ensureMqtt()
{
  if (mqtt.connected()) return;

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMsg);

  Serial.printf("[MQTT] Connecting to %s:%d ...\n", MQTT_HOST, MQTT_PORT);
  while (!mqtt.connected())
  {
    if (mqtt.connect("esp32-s3-display"))
    {
      mqtt.subscribe(TOPIC_CMD_IN);
      Serial.printf("[MQTT] Connected. Subscribed to '%s'\n", TOPIC_CMD_IN);
    }
    else {
      Serial.printf("[MQTT] Connect failed rc=%d. Retry...\n", mqtt.state());
      delay(800);
    }
  }
}

void setup()
{
  Serial.begin(115200);

  // --- TFT 초기화 ---
  pinMode(38, OUTPUT);
  digitalWrite(38, HIGH);   // 백라이트 ON
  tft.init();
  tft.setRotation(1);       // 320x170 가로

  // 부팅 직후 neutral로 1회 렌더
  setMood(NEUTRAL, 0);

  // 네트워크 연결 (연결/성공 로그 출력)
  ensureWiFi();   // → [WiFi] Connected. ... 출력
  ensureMqtt();   // → [MQTT] Connected. ... 출력

  Serial.printf("Ready. Waiting JSON on '%s'\n", TOPIC_CMD_IN);
}

void loop()
{
  // 연결 상태를 지속 점검 (재연결 시에도 로그가 뜸)
  if (WiFi.status() != WL_CONNECTED) ensureWiFi();
  if (!mqtt.connected()) ensureMqtt();
  mqtt.loop();

  // HAPPY/LOVE 유지시간 만료 시 NEUTRAL 복귀 + 로그
  if (state.expireAt != 0)
  {
    if ((int32_t)(millis() - state.expireAt) >= 0)
    {
      setMood(NEUTRAL, 0);
      Serial.println("[STATE] auto back to NEUTRAL");
    }
  }

  delay(5);
}
