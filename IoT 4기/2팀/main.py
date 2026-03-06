# --- EMERGENCY 경보 패턴 함수 ---
def play_emergency_pattern(last_move_time_ref):
    while shared.drowsy_level == 4 and shared.running and buzzer_vib_enabled:
        curr_time = time.time()
        idle_duration = curr_time - last_move_time_ref()
        publish_state_mqtt(4, "EMERGENCY")
# ====== 부저/진동 전체 활성화/비활성화 플래그 및 함수 ======
import time
buzzer_vib_enabled = True  # True: 전체 활성화, False: 전체 비활성화

def buzzer_vib_enable():
    global buzzer_vib_enabled
    buzzer_vib_enabled = True
    print("[SYSTEM] 부저/진동 전체 활성화됨")

def buzzer_vib_disable():
    global buzzer_vib_enabled
    buzzer_vib_enabled = False
    print("[SYSTEM] 부저/진동 전체 비활성화됨")

# ====== 부저/진동 전체 활성화/비활성화 타이머 ======
import threading
from gtts import gTTS
import subprocess
def buzzer_vib_startup_timer():
    buzzer_vib_disable()
    def enable_later():
        time.sleep(20)
        buzzer_vib_enable()
        play_tts_korean("경고 시스템이 활성화되었습니다.")
    threading.Thread(target=enable_later, daemon=True).start()

# ====== TTS(음성 안내) 함수 ======
def play_tts_korean(text):
    def tts_worker():
        try:
            tts = gTTS(text=text, lang='ko')
            tts_path = "/tmp/tts_start.mp3"
            tts.save(tts_path)
            import os
            if not os.path.exists(tts_path):
                print(f"[TTS] 파일 생성 실패: {tts_path}")
                return
            if subprocess.call(["which", "mpg321"], stdout=subprocess.DEVNULL) == 0:
                subprocess.call(["mpg321", tts_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.call(["omxplayer", tts_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                os.remove(tts_path)
            except Exception as e_rm:
                print(f"[TTS] 파일 삭제 실패: {e_rm}")
        except Exception as e:
            print(f"[TTS] 음성 안내 실패: {e}")
    threading.Thread(target=tts_worker, daemon=True).start()

# 프로그램 시작 시 자동 실행
buzzer_vib_startup_timer()


# 부저/진동 동작 전 아래와 같이 사용 예시:
# if buzzer_vib_enabled:
#     ...부저/진동 동작 코드...
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
mqtt_client = mqtt.Client()
def publish_state_mqtt(state, source=""):
    payload = json.dumps({"state": int(state)})
    try:
        if mqtt_client.is_connected():
            mqtt_client.publish("car/status/state", payload, qos=0, retain=True)
            return True
        raise RuntimeError("mqtt_client not connected")
    except Exception as e:
        try:
            publish.single(
                "car/status/state",
                payload,
                hostname=MQTT_HOST,
                port=MQTT_PORT,
                retain=True,
            )
            return True
        except Exception as e2:
            print(f"⚠️ MQTT 상태 전송 실패{source}: {e} / {e2}")
            return False
def publish_heart_mqtt(bpm, source=""):
    payload = json.dumps({"bpm": int(bpm)})
    try:
        if mqtt_client.is_connected():
            mqtt_client.publish("sensor/heart/bpm", payload, qos=0, retain=True)
            return True
        raise RuntimeError("mqtt_client not connected")
    except Exception as e:
        try:
            publish.single(
                "sensor/heart/bpm",
                payload,
                hostname=MQTT_HOST,
                port=MQTT_PORT,
                retain=True,
            )
            return True
        except Exception as e2:
            print(f"⚠️ MQTT 심박 전송 실패{source}: {e} / {e2}")
            return False
import threading
import time
import cv2
import numpy as np
import math
import joblib
import json
import board
import busio
import queue
import os
import subprocess

# --- 얼굴 검출 DNN 네트워크 초기화 ---
prototxt_path = "/home/admin/k-digital/models/deploy.prototxt"
model_path = "/home/admin/k-digital/models/res10_300x300_ssd_iter_140000.caffemodel"
net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)

# --- 외부 라이브러리 ---
from picamera2 import Picamera2
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_adxl34x
from gpiozero import Buzzer, OutputDevice, Button
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import io

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from PIL import Image

# --- 차선 인식 관련 상수 (lane3_compare_3.py에서 이식) ---
import numpy as np

# Canny 엣지 감지
CANNY1 = 50
CANNY2 = 170
BLUR_K = 5

# HoughLinesP
HOUGH_THRESH = 25
HOUGH_MIN_LEN = 30
HOUGH_MAX_GAP = 40
SLOPE_MIN = 0.25
SLOPE_MAX = 8.0

# HLS 색상 마스크
WHITE_L_MIN = 175
WHITE_S_MAX = 140
YELLOW_H_MIN = 15
YELLOW_H_MAX = 40
YELLOW_L_MIN = 80
YELLOW_S_MIN = 90

# 모폴로지
DILATE_K = 3
CLOSE_K = 7

# ====== 보조 마스크(세그멘테이션 대체용) ======
USE_AUX_MASK = True
AUX_CLAHE_CLIP = 2.0
AUX_CLAHE_TILE = (8, 8)
AUX_ADAPT_BLOCK = 31
AUX_ADAPT_C = -5
AUX_OPEN_K = 3
AUX_CLOSE_K = 5

# 사다리꼴 ROI
TRAP_TOP_Y_RATIO = 0.35
TRAP_TOP_W_RATIO = 0.18
TRAP_BOT_W_RATIO = 0.95

# ====== 모드 ======
MODE_EDGE_ONLY = 1
MODE_COLOR_LANE = 2
mode = MODE_COLOR_LANE

# 차선이탈 판정
DEPARTURE_THRESHOLD = 0.18
HOLD_TIME_SEC = 0.50
COOLDOWN_SEC = 1.0
VIB_PULSE_SH = "/home/admin/k-digital/scripts/vib_pulse.sh"
MIN_OK_FRAMES = 10
MAX_RATIO_JUMP = 0.25
ROI_START_RATIO = 0.70
MIN_LANE_WIDTH_RATIO = 0.35
MAX_LANE_WIDTH_RATIO = 0.95
EMA_ALPHA = 0.25

# 전역 EMA 상태
left_ema = None
right_ema = None

# ✅ 차선 인식 임시 비활성화 (필요 시 True로 변경)
ENABLE_LANE = True

# ==========================================
# 1. 전역 상태 공유 클래스 (데이터 허브)
# ==========================================
class GlobalState:
    def __init__(self):
        # 시스템 상태
        self.running = True
        self.system_active = True  # 시작 시 기본 활성화 (토글 스위치로 제어)
        self.toggle_switch = 0  # ✅ 토글 상태: -1(LEFT), 0(OFF), 1(RIGHT)
        # 센서 데이터 (기본값)
        self.drowsy_level = 1      # 1:정상, 2:주의, 3:위험
        self.closed_sec = 0.0
        self.lane_status = "OK"    # OK, DEPART, LANE_CHANGE
        self.lane_ratio = 0.0
        self.bpm = 0.0
        self.steering_angle = 0.0
        self.is_hands_off = False
        # 카메라 프레임 (웹 스트리밍용)
        self.face_frame = None
        self.lane_frame = None
        # 디스플레이 제어 (스레드 안전)
        self.display_frame = None
        self.display_window = "Driver Monitor"
        # 스레드 간 안전한 접근을 위한 락
        self.lock = threading.Lock()
        # manual_label 관련 속성 추가
        self.manual_label = 0

    def toggle_manual_label(self):
        """manual_label 값을 0과 1로 토글"""
        with self.lock:
            self.manual_label = 1 - int(self.manual_label)
            if buzzer_vib_enabled:
                print(f"[DEBUG] toggle_manual_label 호출됨, manual_label={self.manual_label}", flush=True)
            return self.manual_label

    def get_features(self):
        """AI 추론용 feature dict 반환"""
        with self.lock:
            return {
                "drowsy_level": float(self.drowsy_level),
                "closed_sec": float(self.closed_sec),
                "lane_status": float(STATUS_MAP.get(self.lane_status, 0)),
                "lane_ratio": float(self.lane_ratio),
                "steering_angle": float(self.steering_angle),
                "hands_off": float(int(bool(self.is_hands_off))),
                "bpm": float(self.bpm),
            }

    def update_face(self, level, closed_sec):
        with self.lock:
            self.drowsy_level = level
            self.closed_sec = closed_sec

    def update_lane(self, status, ratio):
        with self.lock:
            self.lane_status = status
            self.lane_ratio = ratio

    def update_sensor(self, bpm, angle, hands_off):
        with self.lock:
            self.bpm = bpm
            self.steering_angle = angle
            self.is_hands_off = hands_off
    
    def set_toggle_switch(self, state):
        """✅ 토글 스위치 상태 업데이트"""
        with self.lock:
            self.toggle_switch = state
    
    def set_face_frame(self, frame):
        with self.lock:
            self.face_frame = frame
    
    def set_lane_frame(self, frame):
        with self.lock:
            self.lane_frame = frame
    
    def set_display_frame(self, frame):
        """디스플레이용 프레임 설정"""
        with self.lock:
            self.display_frame = frame
    
    def get_display_frame(self):
        """디스플레이용 프레임 가져오기"""
        with self.lock:
            return self.display_frame

# 전역 객체 생성
STATUS_MAP = {
    "OK": 0,
    "UNSTABLE": 1,
    "NO_LANE": 2,
    "DEPART": 3,
    "EDGE": 4,
}

# AI 모델 및 feature 컬럼 로드
AI_MODEL_PATH = "/home/admin/k-digital/hyuk/drowsy_model.joblib"
try:
    ai_bundle = joblib.load(AI_MODEL_PATH)
    ai_model = ai_bundle["model"]
    ai_features = ai_bundle["features"]
except Exception as e:
    ai_model = None
    ai_features = None
    if buzzer_vib_enabled:
        print(f"❌ [AI] 모델 로드 실패: {e}")

def get_drowsy_probability():
    """AI 모델로 졸음운전 확률 추론"""
    if ai_model is None or ai_features is None:
        return 0.0
    feats = shared.get_features()
    X = np.array([[feats[c] for c in ai_features]], dtype=float)
    try:
        proba = float(ai_model.predict_proba(X)[0, 1])
        return proba
    except Exception as e:
        if buzzer_vib_enabled:
            print(f"❌ [AI] 추론 실패: {e}")
        return 0.0
shared = GlobalState()

# ==========================================
# 2. 하드웨어 설정 (I2C, GPIO)
# ==========================================
i2c = None
accel = None
ads = None
heart_chan = None

try:
    i2c = busio.I2C(board.SCL, board.SDA)
    if buzzer_vib_enabled:
        print("✅ I2C 버스 초기화 성공")
    
    # 가속도 센서 (ADXL345) - 주소: 0x53
    try:
        accel = adafruit_adxl34x.ADXL345(i2c)
        if buzzer_vib_enabled:
            print("✅ ADXL345 센서 초기화 성공")
    except Exception as e:
        if buzzer_vib_enabled:
            print(f"⚠️ ADXL345 센서 초기화 실패 (주소: 0x53): {e}")
        accel = None
    
    # 심박수 센서 (ADS1115) - 주소: 0x48 (기본값)
    try:
        ads = ADS.ADS1115(i2c)
        ads.gain = 2
        heart_chan = AnalogIn(ads, 0)
        if buzzer_vib_enabled:
            print("✅ ADS1115 센서 초기화 성공")
    except Exception as e:
        if buzzer_vib_enabled:
            print(f"⚠️ ADS1115 센서 초기화 실패 (주소: 0x48): {e}")
        ads = None
        heart_chan = None
        
except Exception as e:
    if buzzer_vib_enabled:
        print(f"⚠️ I2C 버스 초기화 실패: {e}")
    if buzzer_vib_enabled:
        print("   💡 팁: i2cdetect -y 1 명령으로 연결된 센서 주소를 확인하세요")

# GPIO 액추에이터
buzzer = None
vib_motor = None
toggle_sw = None

try:
    buzzer = Buzzer(23)
    if buzzer_vib_enabled:
        print("✅ GPIO 23 (Buzzer) 초기화 성공")
except Exception as e:
    if buzzer_vib_enabled:
        print(f"⚠️ GPIO 23 (Buzzer) 초기화 실패: {e}")
    buzzer = None

try:
    vib_motor = OutputDevice(18)
    if buzzer_vib_enabled:
        print("✅ GPIO 18 (Vibration) 초기화 성공")
except Exception as e:
    if buzzer_vib_enabled:
        print(f"⚠️ GPIO 18 (Vibration) 초기화 실패: {e}")
    vib_motor = None

# 진동 모터 완전 비활성화: vib_motor 초기화 코드 제거
# vib_motor = None

try:
    # ✅ 3단계 토글 스위치 (GPIO 27:LEFT, GPIO 17:OFF, GPIO 22:RIGHT)
    # 각 핀은 pull_up=True로 설정 (토글이 눌려있으면 False)
    toggle_left = Button(27, pull_up=True, bounce_time=0.1)
    toggle_center = Button(17, pull_up=True, bounce_time=0.1)
    toggle_right = Button(22, pull_up=True, bounce_time=0.1)
    if buzzer_vib_enabled:
        print("✅ GPIO 27/17/22 (3단계 토글 스위치) 초기화 성공")
    toggle_sw = True  # 토글 스위치가 초기화됨을 나타냄
except Exception as e:
    if buzzer_vib_enabled:
        print(f"⚠️ 3단계 토글 스위치 초기화 실패: {e}")
    toggle_left = None
    toggle_center = None
    toggle_right = None
    toggle_sw = None

# MQTT 설정
MQTT_HOST = os.environ.get("MQTT_HOST", "192.168.0.13")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
if buzzer_vib_enabled:
    print(f"✅ MQTT 설정: host={MQTT_HOST} port={MQTT_PORT}")

mqtt_client = mqtt.Client()
try:
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    if buzzer_vib_enabled:
        print(f"⚠️ MQTT 연결 실패: {e}")

# ==========================================
# 차선 감지 함수들 (lane3_compare_3.py에서 이식)
# ==========================================

def trapezoid_mask(h, w):
    """사다리꼴 ROI 마스크 생성"""
    y_top = int(h * TRAP_TOP_Y_RATIO)
    top_w = int(w * TRAP_TOP_W_RATIO)
    bot_w = int(w * TRAP_BOT_W_RATIO)
    x_center = w // 2
    
    pts = np.array([
        [x_center - bot_w // 2, h - 1],
        [x_center - top_w // 2, y_top],
        [x_center + top_w // 2, y_top],
        [x_center + bot_w // 2, h - 1],
    ], dtype=np.int32)
    
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    return mask, pts

def color_lane_mask_hls(roi_bgr):
    """HLS 기반 흰색/황색 차선 마스크"""
    hls = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HLS)
    H, L, S = cv2.split(hls)

    white_l = cv2.inRange(L, WHITE_L_MIN, 255)
    white_s = cv2.inRange(S, 0, WHITE_S_MAX)
    white = cv2.bitwise_and(white_l, white_s)

    yellow_h = cv2.inRange(H, YELLOW_H_MIN, YELLOW_H_MAX)
    yellow_l = cv2.inRange(L, YELLOW_L_MIN, 255)
    yellow_s = cv2.inRange(S, YELLOW_S_MIN, 255)
    yellow = cv2.bitwise_and(yellow_h, cv2.bitwise_and(yellow_l, yellow_s))

    return cv2.bitwise_or(white, yellow)

def roi_edges(roi_bgr):
    """Canny 엣지 감지"""
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    if BLUR_K and BLUR_K >= 3:
        gray = cv2.GaussianBlur(gray, (BLUR_K, BLUR_K), 0)
    edges = cv2.Canny(gray, CANNY1, CANNY2)
    return edges

def build_aux_mask(roi_bgr):
    """조도 변화에 강한 보조 마스크(간이 세그멘테이션 역할)"""
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=AUX_CLAHE_CLIP, tileGridSize=AUX_CLAHE_TILE)
    gray_eq = clahe.apply(gray)

    mask = cv2.adaptiveThreshold(
        gray_eq, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        AUX_ADAPT_BLOCK,
        AUX_ADAPT_C
    )

    if AUX_OPEN_K and AUX_OPEN_K >= 3:
        k = np.ones((AUX_OPEN_K, AUX_OPEN_K), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)

    if AUX_CLOSE_K and AUX_CLOSE_K >= 3:
        k = np.ones((AUX_CLOSE_K, AUX_CLOSE_K), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

    h, w = mask.shape[:2]
    trap, _ = trapezoid_mask(h, w)
    mask = cv2.bitwise_and(mask, trap)
    return mask

def build_lane_binary(roi_bgr, canny1=CANNY1, canny2=CANNY2, white_l_min=WHITE_L_MIN):
    """이진 차선 이미지 생성"""
    # 엣지 + 컬러 마스크는 튜닝 파라미터로 조정
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    if BLUR_K and BLUR_K >= 3:
        gray = cv2.GaussianBlur(gray, (BLUR_K, BLUR_K), 0)
    edges = cv2.Canny(gray, canny1, canny2)

    hls = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HLS)
    H, L, S = cv2.split(hls)
    white_l = cv2.inRange(L, white_l_min, 255)
    white_s = cv2.inRange(S, 0, WHITE_S_MAX)
    white = cv2.bitwise_and(white_l, white_s)

    yellow_h = cv2.inRange(H, YELLOW_H_MIN, YELLOW_H_MAX)
    yellow_l = cv2.inRange(L, YELLOW_L_MIN, 255)
    yellow_s = cv2.inRange(S, YELLOW_S_MIN, 255)
    yellow = cv2.bitwise_and(yellow_h, cv2.bitwise_and(yellow_l, yellow_s))
    color_mask = cv2.bitwise_or(white, yellow)

    if DILATE_K >= 2:
        k = np.ones((DILATE_K, DILATE_K), np.uint8)
        edges_d = cv2.dilate(edges, k, iterations=1)
    else:
        edges_d = edges

    binary = cv2.bitwise_and(color_mask, edges_d)

    if USE_AUX_MASK:
        aux_mask = build_aux_mask(roi_bgr)
        binary = cv2.bitwise_or(binary, aux_mask)

    h, w = binary.shape[:2]
    trap, pts = trapezoid_mask(h, w)
    binary = cv2.bitwise_and(binary, trap)

    if CLOSE_K >= 3:
        k = np.ones((CLOSE_K, CLOSE_K), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k)

    return binary, edges, color_mask, pts

def average_lane_line(lines, side, h):
    """라인들의 평균 계산"""
    if lines is None:
        return None
    
    ms, bs = [], []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0:
            continue
        m = dy / dx
        
        if abs(m) < SLOPE_MIN or abs(m) > SLOPE_MAX:
            continue
        if side == "left" and m >= 0:
            continue
        if side == "right" and m <= 0:
            continue
        
        b = y1 - m * x1
        ms.append(m)
        bs.append(b)
    
    if not ms:
        return None
    
    m = float(np.mean(ms))
    b = float(np.mean(bs))
    
    y_bottom = h - 1
    y_top = int(h * 0.35)
    x_bottom = int((y_bottom - b) / m)
    x_top = int((y_top - b) / m)
    
    return (x_bottom, y_bottom, x_top, y_top)

def ema_update(prev, curr, alpha):
    """지수이동평균 필터"""
    if curr is None:
        return prev
    if prev is None:
        return curr
    return tuple(int((1 - alpha) * p + alpha * c) for p, c in zip(prev, curr))

def detect_and_draw_lanes(roi_bgr, binary, trap_pts):
    """차선 감지 및 그리기"""
    global left_ema, right_ema
    
    h, w = binary.shape[:2]
    
    lines = cv2.HoughLinesP(
        binary,
        rho=1,
        theta=np.pi / 180,
        threshold=HOUGH_THRESH,
        minLineLength=HOUGH_MIN_LEN,
        maxLineGap=HOUGH_MAX_GAP
    )
    
    left = average_lane_line(lines, "left", h)
    right = average_lane_line(lines, "right", h)
    
    # EMA 안정화
    left_ema = ema_update(left_ema, left, EMA_ALPHA)
    right_ema = ema_update(right_ema, right, EMA_ALPHA)
    left = left_ema
    right = right_ema
    
    overlay = roi_bgr.copy()
    cv2.polylines(overlay, [trap_pts], True, (0, 255, 255), 1)
    
    lane_color = (0, 255, 0)
    thick = 6
    
    offset_ratio = None
    lane_width_ratio = None
    
    if left is not None:
        cv2.line(overlay, (left[0], left[1]), (left[2], left[3]), lane_color, thick)
    if right is not None:
        cv2.line(overlay, (right[0], right[1]), (right[2], right[3]), lane_color, thick)
    
    if left is not None and right is not None:
        lane_center = (left[0] + right[0]) / 2.0
        car_center = w / 2.0
        offset_px = lane_center - car_center
        offset_ratio = float(offset_px / (w / 2.0))
        
        lane_width = abs(right[0] - left[0])
        lane_width_ratio = float(lane_width / float(w))
        
        pts = np.array([
            [left[0], left[1]],
            [left[2], left[3]],
            [right[2], right[3]],
            [right[0], right[1]],
        ], dtype=np.int32)
        
        shade = overlay.copy()
        cv2.fillPoly(shade, [pts], (0, 255, 0))
        overlay = cv2.addWeighted(shade, 0.20, overlay, 0.80, 0)
        
        cv2.circle(overlay, (int(lane_center), h - 8), 6, (0, 255, 255), -1)
        cv2.circle(overlay, (int(car_center), h - 8), 6, (255, 0, 0), -1)
    
    return overlay, offset_ratio, lane_width_ratio

def to_bgr(gray):
    if gray is None:
        return None
    if len(gray.shape) == 2:
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return gray

# ==========================================
def run_face_detection():
    if buzzer_vib_enabled:
        print("👁️ 얼굴 인식 스레드 초기화 중...")

    import cv2
    import numpy as np
    from pathlib import Path

    def clamp(x, lo, hi):
        return max(lo, min(hi, x))

    # 68-landmark eye indices
    LEFT_EYE_IDX = [36, 37, 38, 39, 40, 41]
    RIGHT_EYE_IDX = [42, 43, 44, 45, 46, 47]

    def calc_ear(eye_pts):
        p1, p2, p3, p4, p5, p6 = eye_pts
        A = np.linalg.norm(p2 - p6)
        B = np.linalg.norm(p3 - p5)
        C = np.linalg.norm(p1 - p4)
        if C == 0:
            return 0.0
        return (A + B) / (2.0 * C)

    # 모델 파일 경로 설정 (현재 파일 위치 기준)
    BASE_DIR = Path(__file__).resolve().parent
    PROTO = BASE_DIR / "models" / "deploy.prototxt"
    CAFFE = BASE_DIR / "models" / "res10_300x300_ssd_iter_140000.caffemodel"
    LBF = BASE_DIR / "models" / "lbfmodel.yaml"

    # 모델 파일 확인
    if not PROTO.exists() or not CAFFE.exists() or not LBF.exists():
        if buzzer_vib_enabled:
            print("❌ [Face] 모델 파일을 찾을 수 없습니다! models 폴더를 확인하세요.")
        return

    # --- [모델 로드] ---
    try:
        if not hasattr(cv2, "face"):
            raise RuntimeError("cv2.face 가 없습니다. opencv-contrib-python 로 설치했는지 확인하세요.")
        face_net = cv2.dnn.readNetFromCaffe(str(PROTO), str(CAFFE))
        facemark = cv2.face.createFacemarkLBF()
        facemark.loadModel(str(LBF))
    except Exception as e:
        if buzzer_vib_enabled:
            print(f"❌ [Face] 모델 로드 에러: {e}")
        return

    # --- [카메라 설정] ---
    cam_face = None

    try:
        if buzzer_vib_enabled:
            print("🔄 Picamera2(카메라 1) 초기화 중...")
        cam_face = Picamera2(camera_num=1)  # ✅ 카메라 1: 얼굴 인식
        # 센서 전체 영역(원본 해상도)으로 입력
        config = cam_face.create_preview_configuration(main={"size": (1640, 1232), "format": "RGB888"})
        cam_face.configure(config)
        try:
            full_crop = cam_face.camera_properties.get("ScalerCropMaximum")
            if full_crop:
                cam_face.set_controls({"ScalerCrop": full_crop})
                if buzzer_vib_enabled:
                    print("✅ [Face] 카메라 크롭 초기화(줌 해제)")
        except Exception as e:
            if buzzer_vib_enabled:
                print(f"⚠️ [Face] 카메라 크롭 초기화 실패: {e}")
        # 프레임레이트(FPS) 설정: 30fps로 시도
        try:
            cam_face.set_controls({"FrameDurationLimits": (16666, 16666)})  # 1초/60 = 16666us
            if buzzer_vib_enabled:
                print("✅ [Face] 카메라 FPS 60으로 설정")
        except Exception as e:
            if buzzer_vib_enabled:
                print(f"⚠️ [Face] 카메라 FPS 설정 실패: {e}")
        cam_face.start()
        if buzzer_vib_enabled:
            print("✅ [Face] Picamera2(카메라 1) 초기화 성공")
    except Exception as e:
        if buzzer_vib_enabled:
            print(f"❌ [Face] Picamera2 초기화 실패: {e}")
        import traceback
        if buzzer_vib_enabled:
            traceback.print_exc()
        return

    # =========================
    # Eye-only thresholds
    # =========================
    MILD_SEC = 0.55
    DANGER_SEC = 1.30
    FACE_MISS_GRACE_SEC = 0.60

    # =========================
    # Processing size
    # =========================
    PROC_W, PROC_H = 640, 480  # 처리용 해상도(시야각 유지, 화질만 저하)

    # =========================
    # Stability controls
    # =========================
    DETECT_EVERY = 2  # 얼굴 인식 연산을 1프레임에 한 번만 수행
    frame_i = 0
    best_box = None
    best_conf = 0.0

    miss_lbf = 0
    MISS_LBF_REDETECT = 2

    miss_face = 0
    MISS_FACE_REDETECT = 4

    PAD_RATIO = 0.15

    # =========================
    # EAR calibration
    # =========================
    USE_EAR_CALIB = True
    CALIB_SEC = 10
    ear_samples = []
    calib_start = time.time()
    ear_thresh = 0.225

    EAR_BASE_OFFSET = 0.06
    EAR_OPEN_BONUS = 0.03
    EAR_ADAPTIVE = True
    EAR_EMA_ALPHA = 0.03
    EAR_OPEN_MARGIN = 0.02
    RELEASE_DECAY = 3.0
    EAR_SMOOTH_ALPHA = 0.25

    # =========================
    # State vars
    # =========================
    state = 0  # 0: NORMAL, 1: CAUTION, 2: WARNING, 3: DANGER, 4: EMERGENCY
    closed_sec = 0.0
    last_face_time = time.time()
    prev_t = time.time()
    ear_min_seen = 9.0
    last_ear = None
    ear_ema = None
    ear_calibrated = False
    open_ear_ema = None

    print("👁️ 얼굴 인식 감시 시작!")
    last_published_state = None

    while shared.running:
        # FPS 측정용 변수
        # if 'fps_prev_time' not in locals():
        #     fps_prev_time = time.time()
        # Picamera2 프레임 읽기
        try:
            frame = cam_face.capture_array()
            # Picamera2는 RGB로 반환하므로, OpenCV에서 표시할 때 BGR로 변환
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            # FPS 계산 및 출력
            # fps_now = time.time()
            # fps = 1.0 / (fps_now - fps_prev_time) if (fps_now - fps_prev_time) > 0 else 0
            # print(f"[FaceCam FPS] {fps:.2f}")
            # fps_prev_time = fps_now
        except Exception as e:
            print(f"⚠️ [Face] 프레임 읽기 실패: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(0.1)
            continue

        now = time.time()
        dt = clamp(now - prev_t, 0.0, 0.2)
        prev_t = now

        # 센서 전체 영역을 받아와서 처리 단계에서만 리사이즈
        proc = cv2.resize(frame, (PROC_W, PROC_H), interpolation=cv2.INTER_AREA)
        H, W = proc.shape[:2]
        frame_i += 1

        detect_every_now = 1 if state == 3 else DETECT_EVERY
        need_redetect = (best_box is None) or (frame_i % detect_every_now == 0)
        if miss_lbf >= MISS_LBF_REDETECT:
            need_redetect = True
        if miss_face >= MISS_FACE_REDETECT:
            need_redetect = True

        # =========================
        # Face detect (DNN)
        # =========================
        if need_redetect:
            blob = cv2.dnn.blobFromImage(proc, 1.0, (300, 300), (104.0, 177.0, 123.0))
            face_net.setInput(blob)
            detections = face_net.forward()

            best_score = -1e9
            best_box = None
            best_conf = 0.0

            cx0, cy0 = W / 2.0, H / 2.0
            frame_area = float(W * H)

            for i in range(detections.shape[2]):
                conf = float(detections[0, 0, i, 2])
                if conf < 0.5:
                    continue
                box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                x1, y1, x2, y2 = box.astype(int)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(W - 1, x2), min(H - 1, y2)
                bw = x2 - x1
                bh = y2 - y1
                if bw < 40 or bh < 40:
                    continue
                area_ratio = (bw * bh) / max(1.0, frame_area)
                cx = x1 + bw / 2.0
                cy = y1 + bh / 2.0
                dist = ((cx - cx0) ** 2 + (cy - cy0) ** 2) ** 0.5
                dist_ratio = dist / max(1.0, (min(W, H) / 2.0))
                score = conf - 0.9 * area_ratio - 0.35 * dist_ratio
                if score > best_score:
                    best_score = score
                    best_conf = conf
                    best_box = (x1, y1, bw, bh)
            miss_lbf = 0
            miss_face = 0

        found_face = (best_box is not None) and (best_conf >= 0.5)

        # =========================
        # Landmark + EAR
        # =========================
        if found_face:
            last_face_time = now
            x, y, bw, bh = best_box

            padw = int(bw * PAD_RATIO)
            padh = int(bh * PAD_RATIO)
            rx1 = max(0, x - padw)
            ry1 = max(0, y - padh)
            rx2 = min(W - 1, x + bw + padw)
            ry2 = min(H - 1, y + bh + padh)

            roi = proc[ry1:ry2, rx1:rx2]
            if roi.size == 0:
                best_box = None
                continue

            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            fx, fy = x - rx1, y - ry1
            faces = np.array([[fx, fy, bw, bh]])

            ok, landmarks = facemark.fit(gray_roi, faces)

            cv2.rectangle(proc, (rx1, ry1), (rx2, ry2), (255, 255, 0), 1)
            cv2.rectangle(proc, (x, y), (x + bw, y + bh), (0, 255, 0), 2)

            if not ok:
                miss_lbf += 1
                cv2.putText(proc, f"Landmark failed ({miss_lbf})", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                if miss_lbf >= MISS_LBF_REDETECT:
                    best_box = None
                closed_sec = 0.0
                state = 1
                last_ear = None
            else:
                miss_lbf = 0
                pts = landmarks[0][0].astype(np.float32)
                pts[:, 0] += rx1
                pts[:, 1] += ry1

                for idx in LEFT_EYE_IDX + RIGHT_EYE_IDX:
                    px, py = int(pts[idx][0]), int(pts[idx][1])
                    cv2.circle(proc, (px, py), 2, (0, 255, 255), -1)

                left_eye = [pts[i] for i in LEFT_EYE_IDX]
                right_eye = [pts[i] for i in RIGHT_EYE_IDX]
                ear = (calc_ear(left_eye) + calc_ear(right_eye)) / 2.0
                last_ear = float(ear)
                if ear_ema is None:
                    ear_ema = ear
                else:
                    ear_ema = (1.0 - EAR_SMOOTH_ALPHA) * ear_ema + EAR_SMOOTH_ALPHA * ear
                ear_used = float(ear_ema)
                ear_min_seen = min(ear_min_seen, ear_used)

                if USE_EAR_CALIB and (now - calib_start) < CALIB_SEC:
                    if ear_used > 0.20:
                        ear_samples.append(ear_used)
                    cv2.putText(proc, f"CALIB EAR... {now - calib_start:.1f}/{CALIB_SEC:.1f}s",
                                (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 200), 2)

                if USE_EAR_CALIB and (not ear_calibrated) and (now - calib_start) >= CALIB_SEC and len(ear_samples) >= 12:
                    base = float(np.median(np.array(ear_samples, dtype=np.float32)))
                    ear_thresh = clamp(base - EAR_BASE_OFFSET, 0.17, 0.32)
                    open_ear_ema = base
                    ear_calibrated = True

                if EAR_ADAPTIVE and open_ear_ema is not None:
                    if ear_used > ear_thresh + EAR_OPEN_MARGIN:
                        open_ear_ema = (1.0 - EAR_EMA_ALPHA) * open_ear_ema + EAR_EMA_ALPHA * ear_used
                        ear_thresh = clamp(open_ear_ema - EAR_BASE_OFFSET, 0.17, 0.32)

                ear_open_thresh = ear_thresh + EAR_OPEN_BONUS

                if ear_used < ear_thresh:
                    closed_sec += dt
                elif ear_used > ear_open_thresh:
                    closed_sec = 0.0
                else:
                    closed_sec = max(0.0, closed_sec - RELEASE_DECAY * dt)

                # AI 확률(p), closed_sec, hands_off_sec 병행 단계 결정 (디바운싱 적용)
                if not hasattr(shared, 'confirmed_level'):
                    shared.confirmed_level = 0
                    shared.pending_level = 0
                    shared.pending_start_time = None

                p = get_drowsy_probability()  # TODO: 실제 AI 모델 inference 함수로 대체
                hands_off_sec = shared.is_hands_off if hasattr(shared, 'is_hands_off') else 0.0
                prev_state = shared.confirmed_level
# -----------------------------------------------------------------
                # [수정된 로직] 안전 우선 순위 결정 (Safety-First Logic)
                # 원칙 1: 위험도가 높아질 때는 단계 건너뛰기 허용 (Jump-Up)
                # 원칙 2: 위험도가 낮아질 때는 히스테리시스 적용 (Slow-Down)
                # -----------------------------------------------------------------
                
                # 1. 각 단계별 진입(상승) 조건 정의 (OR 조건)
                # hands_off_sec가 늘어나면 즉시 상위 조건이 True가 됨
                cond_lev_4 = (p >= 0.92 or closed_sec >= 3.0 or hands_off_sec >= 10.0)
                cond_lev_3 = (p >= 0.75 or closed_sec >= 2.0 or hands_off_sec >= 5.0)
                cond_lev_2 = (p >= 0.45 or closed_sec >= 1.0 or hands_off_sec >= 3.0)
                cond_lev_1 = (p >= 0.28 or closed_sec >= 0.5 or hands_off_sec >= 2.0)

                calculated_level = prev_state  # 기본값 유지

                # [FAST RECOVERY 예외 처리] - 최우선 (완화)
                if hands_off_sec < 1.0 and p < 0.80 and closed_sec < 2.5:
                    calculated_level = 0

                # 2. 상승 로직 (위험 감지 시 즉시 승격)
                elif cond_lev_4:
                    calculated_level = 4
                elif cond_lev_3 and prev_state < 3:
                    calculated_level = 3
                elif cond_lev_2 and prev_state < 2:
                    calculated_level = 2
                elif cond_lev_1 and prev_state < 1:
                    calculated_level = 1

                # 3. 하강/유지 로직 (상승 조건이 없을 때만 실행)
                # 히스테리시스: 현재 상태에서 내려가기 위한 '충분한 회복' 확인
                elif prev_state == 4:
                    if hands_off_sec < 2.0 and p < 0.50 and closed_sec < 0.5:
                        calculated_level = 0
                    elif p < 0.80 and closed_sec < 2.5 and hands_off_sec < 8.0:
                        calculated_level = 3
                    else:
                        calculated_level = 4  # 유지

                elif prev_state == 3:
                    if hands_off_sec < 2.0 and p < 0.50 and closed_sec < 0.5:
                        calculated_level = 0
                    elif p < 0.60 and closed_sec < 1.5 and hands_off_sec < 4.0:
                        calculated_level = 2
                    else:
                        calculated_level = 3  # 유지

                elif prev_state == 2:
                    if hands_off_sec < 2.0 and p < 0.50 and closed_sec < 0.5:
                        calculated_level = 0
                    elif p < 0.30 and closed_sec < 1.2 and hands_off_sec < 3.0:
                        calculated_level = 1
                    else:
                        calculated_level = 2  # 유지

                elif prev_state == 1:
                    if p < 0.18 and closed_sec < 0.8 and hands_off_sec < 1.7:
                        calculated_level = 0
                    else:
                        calculated_level = 1  # 유지

                else:
                    calculated_level = 0  # prev_state == 0 이고 상승 조건도 없으면

                now = time.time()
                # 상태 유지 필터 적용
                if calculated_level != shared.confirmed_level:
                    if shared.pending_level != calculated_level:
                        shared.pending_level = calculated_level
                        shared.pending_start_time = now
                    elif shared.pending_start_time and (now - shared.pending_start_time) >= 0.5:
                        shared.confirmed_level = shared.pending_level
                        shared.drowsy_level = shared.confirmed_level
                else:
                    shared.pending_level = shared.confirmed_level
                    shared.pending_start_time = None

                state = shared.confirmed_level

                cv2.putText(proc, f"FaceConf:{best_conf:.2f}  EAR:{ear_used:.3f}  TH:{ear_thresh:.3f}  OPEN:{ear_open_thresh:.3f}",
                            (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
                cv2.putText(proc, f"closed_sec:{closed_sec:.2f}  ear_min:{ear_min_seen:.3f}",
                            (20, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2)

        else:
            miss_face += 1
            last_ear = None
            if (now - last_face_time) > FACE_MISS_GRACE_SEC:
                closed_sec = 0.0
                state = 1

            cv2.putText(proc, f"No face ({miss_face})", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

            if miss_face >= MISS_FACE_REDETECT:
                best_box = None

        # =========================
        # UI: STATE 표시 (5단계)
        # =========================
        state_text = {
            0: "STATE: NORMAL",
            1: "STATE: CAUTION",
            2: "STATE: WARNING",
            3: "STATE: DANGER!",
            4: "STATE: EMERGENCY!!"
        }
        color_map = {
            0: (102, 255, 102),    # 연두색 (Normal)
            1: (255, 255, 102),      # 노란색 (Caution)
            2: (224, 129, 34),      # 주황색 (Warning)
            3: (255, 25, 0),        # 빨간색 (Danger)
            4: (163, 16, 0)         # 진홍색 (Emergency)
        }
        # p 값이 없는 경우(얼굴 미검출) 기본값 0.0
        if 'p' not in locals():
            p = 0.0
        cv2.putText(proc, f"{state_text.get(state, 'STATE: ?')} {p:.2f}", (20, 175), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color_map.get(state, (255,255,255)), 3)

        # --- [공유 변수 업데이트 (매우 중요)] ---
        shared.update_face(state, float(closed_sec))
        shared.set_face_frame(proc)
        shared.set_display_frame(proc)

        # --- MQTT 상태 전송 (WARNING/DANGER 포함) ---
        if state != last_published_state:
            if publish_state_mqtt(state, "(FACE)"):
                last_published_state = state

    # 종료 처리
    if cam_face is not None:
        cam_face.stop()
    cv2.destroyAllWindows()
    print("👁️ 얼굴 인식 스레드 종료")

# ==========================================
# 4. 스레드 2: 차선 인식 (Lane Thread)
# ==========================================
def run_lane_detection():
    if not ENABLE_LANE:
        print("⛔ 차선 인식 비활성화 상태입니다.")
        return
    print("🛣️ 차선 인식 스레드 시작 (lane3_final 로직)...")

    def safe_run(cmd):
        try:
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    try:
        print("🔄 Picamera2(카메라 0) 초기화 중...")
        cam = Picamera2(camera_num=0)
        config = cam.create_preview_configuration(main={"size": (640, 360), "format": "RGB888"})
        cam.configure(config)
        cam.start()
        print("✅ [Lane] Picamera2(카메라 0) 초기화 성공")
    except Exception as e:
        print(f"❌ [Lane] 카메라 초기화 실패: {e}")
        return

    last_proc = 0.0
    PROCESS_INTERVAL = 0.10
    last_status = "BOOT"
    last_ratio = None
    last_lane_w = None
    last_out = None
    last_debug_time = 0.0
    last_mask_full = None
    last_color_full = None
    last_edges_full = None

    dep_start = None
    last_vib = 0.0

    # 품질 게이트 상태
    ok_streak = 0
    prev_ratio = None
    debug_count = 0

    while shared.running:
        try:
            frame_rgb = cam.capture_array()
            # Picamera2는 RGB로 반환하므로, OpenCV에서 표시할 때 BGR로 변환
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            H, W = frame_bgr.shape[:2]
            y0 = int(H * ROI_START_RATIO)

            now = time.time()
            if (now - last_proc) >= PROCESS_INTERVAL:
                roi = frame_bgr[y0:H, 0:W]

                # 1) binary / edges / color_mask 생성 (기본 파라미터)
                binary, edges, color_mask, trap_pts = build_lane_binary(roi)

                # 2) 모드별 오버레이
                if mode == MODE_EDGE_ONLY:
                    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                    cm_bgr = cv2.cvtColor(color_mask, cv2.COLOR_GRAY2BGR)
                    overlay_roi = cv2.addWeighted(roi, 1.0, edges_bgr, 0.9, 0)
                    overlay_roi = cv2.addWeighted(overlay_roi, 1.0, cm_bgr, 0.5, 0)
                    ratio = None
                    lane_w = None
                    status = "EDGE"
                else:
                    overlay_roi, ratio, lane_w = detect_and_draw_lanes(roi, binary, trap_pts)
                    status = "OK" if (ratio is not None and lane_w is not None) else "NO_LANE"

                # 3) 왼쪽(전체 프레임) 복원
                out_full = frame_bgr.copy()
                out_full[y0:H, 0:W] = overlay_roi
                last_out = out_full

                # 4) 오른쪽 디버그: 최종 binary / color_mask / edges 저장
                mask_full = np.zeros((H, W), dtype=np.uint8)
                mask_full[y0:H, 0:W] = binary
                last_mask_full = mask_full

                color_full = np.zeros((H, W), dtype=np.uint8)
                color_full[y0:H, 0:W] = color_mask
                last_color_full = color_full

                edges_full = np.zeros((H, W), dtype=np.uint8)
                edges_full[y0:H, 0:W] = edges
                last_edges_full = edges_full

                last_ratio = ratio
                last_lane_w = lane_w

                # 5) 진동 로직(품질 게이트 포함) - lane3_final 조건 복원
                if mode == MODE_COLOR_LANE and ratio is not None and lane_w is not None:
                    width_ok = (MIN_LANE_WIDTH_RATIO <= lane_w <= MAX_LANE_WIDTH_RATIO)

                    jump_ok = True
                    if isinstance(prev_ratio, (int, float)):
                        if abs(ratio - prev_ratio) >= MAX_RATIO_JUMP:
                            jump_ok = False

                    if width_ok and jump_ok:
                        ok_streak += 1
                    else:
                        ok_streak = 0

                    prev_ratio = ratio

                    # 안정화 완료 후에만 진동 허용
                    if ok_streak >= MIN_OK_FRAMES:
                        # 방향지시등이 켜져 있으면 차선 변경 모드로 간주 (경보/진동 제외)
                        if shared.toggle_switch != 0:
                            dep_start = None
                        else:
                            departed = abs(ratio) >= DEPARTURE_THRESHOLD
                            if departed:
                                status = "DEPART"
                                if dep_start is None:
                                    dep_start = now
                                if (now - dep_start) >= HOLD_TIME_SEC and (now - last_vib) >= COOLDOWN_SEC:
                                    # 진동 완전 비활성화: safe_run(["/bin/bash", VIB_PULSE_SH]) 호출 제거
                                    publish.single(
                                        "sensor/ear",
                                        '{"status":"DANGER"}',
                                        hostname=MQTT_HOST,
                                        port=MQTT_PORT,
                                    )
                                    last_vib = now
                            else:
                                dep_start = None
                                status = "OK"
                    else:
                        dep_start = None
                        status = "UNSTABLE"

                else:
                    ok_streak = 0
                    prev_ratio = None
                    dep_start = None
                    if mode == MODE_EDGE_ONLY:
                        status = "EDGE"
                    else:
                        status = "NO_LANE"

                # 상태 확정 후 갱신
                last_status = status
                last_proc = now

                # ✅ 상태 디버깅 메시지
                now_debug = time.time()
                if now_debug - last_debug_time >= 2.0:
                    toggle_names = {-1: "LEFT", 0: "OFF", 1: "RIGHT"}
                    turn_sig = toggle_names.get(shared.toggle_switch, "?")
                    print(
                        f"🛣️ [Lane] 상태:{last_status} | 토글:{turn_sig} | ratio:{last_ratio} | laneW:{last_lane_w}",
                        flush=True
                    )
                    last_debug_time = now_debug

            # ===== 표시 =====
            left = last_out if last_out is not None else frame_bgr
            # Build a more informative right-side diagnostic view
            if last_color_full is not None and last_edges_full is not None:
                cm_bgr = cv2.cvtColor(last_color_full, cv2.COLOR_GRAY2BGR)
                ed_bgr = cv2.cvtColor(last_edges_full, cv2.COLOR_GRAY2BGR)

                # color_mask -> green channel, edges -> red channel for visibility
                vis = np.zeros_like(cm_bgr)
                vis[:, :, 1] = cm_bgr[:, :, 0]
                vis[:, :, 2] = ed_bgr[:, :, 0]
                right = vis
            else:
                right = to_bgr(last_mask_full)
                if right is None:
                    right = np.zeros_like(left)

            h, w = left.shape[:2]
            right = cv2.resize(right, (w, h))
            canvas = np.hstack([left, right])

            # ROI 경계선(노란색)
            cv2.line(canvas, (0, y0), (w - 1, y0), (0, 255, 255), 2)
            cv2.line(canvas, (w, y0), (w + w - 1, y0), (0, 255, 255), 2)

            # 공유 변수 업데이트
            shared.update_lane(last_status if last_status else "NO_LANE", last_ratio if isinstance(last_ratio, (int, float)) else 0.0)
            shared.set_lane_frame(canvas)

        except Exception as e:
            print(f"❌ [Lane] 프레임 처리 에러: {e}")
            time.sleep(0.1)

    cam.stop()
    print("🛣️ 차선 인식 스레드 종료")

# ==========================================
# 5. 스레드 3: 센서 융합 및 제어 (Control Thread)
# ==========================================
def run_control_logic():
    print("🎮 센서 제어 및 경보 스레드 시작...")
    
    # 파라미터
    ALPHA = 0.15
    IDLE_THRESHOLD = 1.0
    SUDDEN_RATE_UP = 110.0
    SUDDEN_RATE_DOWN = 80.0
    DANGER_TIME = 10.0
    HEART_PEAK_DELTA = 200  # ✅ 심박 피크 감지 임계값(환경에 따라 조정)
    ENABLE_HANDS_OFF = True  # ✅ 핸들 무조작 경보 임시 비활성화
    HANDLE_CENTER_ANGLE = 170.0
    filtered_angle = 0
    bpm = 0.0  # ✅ BPM 초기값 설정
    last_published_state_ctrl = None
    last_publish_time_ctrl = 0.0
    last_bpm_publish_time = 0.0
    
    # 심박수 변수
    last_beat_time = time.time()
    samples = []
    heart_debug_count = 0
    
    # 경보 상태
    alert_active = False
    toggle_check_count = 0
    prev_toggle_state = None
    idle_status_count = 0
    last_angle = 0.0
    prev_sample_angle = 0.0
    prev_sample_time = time.time()
    sample_initialized = False
    last_move_time = time.time()
    sudden_detected = False
    hands_off_active = False

    while shared.running:
        # ✅ 카메라는 항상 켜져있음 (시스템 항상 활성화)
        shared.system_active = True
        
        # 1. 3단계 토글 스위치 확인 (차선 변경 신호만 담당)
        toggle_state = 0  # 기본값: OFF
        
        if toggle_sw is not None:
            # ✅ 3단계 토글 상태 읽기 (방향 지시등)
            # 토글 위치에 따라 해당 핀이 True가 됨
            left_pressed = toggle_left.is_pressed if toggle_left else False
            center_pressed = toggle_center.is_pressed if toggle_center else False
            right_pressed = toggle_right.is_pressed if toggle_right else False
            
            # ✅ 각 위치를 명확하게 구분
            if left_pressed and not center_pressed and not right_pressed:
                toggle_state = -1  # LEFT (좌회전 신호)
            elif center_pressed and not left_pressed and not right_pressed:
                toggle_state = 0   # CENTER (신호 없음)
            elif right_pressed and not center_pressed and not left_pressed:
                toggle_state = 1   # RIGHT (우회전 신호)
            else:
                # 이상 상태: 여러 버튼이 눌려있음 → OFF로 처리
                toggle_state = 0
        
        # ✅ 토글 상태 저장 (차선 변경 신호용)
        shared.set_toggle_switch(toggle_state)
        
        toggle_check_count += 1
        if prev_toggle_state is None or toggle_state != prev_toggle_state:
            toggle_names = {-1: "◀ LEFT", 0: "● OFF", 1: "RIGHT ▶"}
            prev_toggle_state = toggle_state
        
        # --- 카메라는 항상 켜져있음 (아래 로직 항상 수행) ---

        # 2. 핸들 조향각 (ADXL345)
        sensor_ok = False
        if accel is not None:
            try:
                x, y, z = accel.acceleration
                raw_angle = math.degrees(math.atan2(x, y))
                centered_angle = ((raw_angle - HANDLE_CENTER_ANGLE + 180) % 360) - 180
                filtered_angle = (ALPHA * centered_angle) + ((1.0 - ALPHA) * filtered_angle)
                sensor_ok = True
            except Exception as e:
                print(f"⚠️ ADXL345 읽기 실패: {e}")
                filtered_angle = 0.0

        sudden_alert = False
        if sensor_ok:
            curr_time = time.time()
            if not sample_initialized:
                prev_sample_angle = filtered_angle
                prev_sample_time = curr_time
                sample_initialized = True
                angular_rate = 0.0
                angle_diff = abs(filtered_angle - last_angle)
            else:
                dt = max(curr_time - prev_sample_time, 1e-3)
                sample_diff = abs(filtered_angle - prev_sample_angle)
                angular_rate = sample_diff / dt
                angle_diff = abs(filtered_angle - last_angle)

            # --- [급격한 조향 감지 + 무조작 타이머 갱신] ---
            # 첫 샘플 초기화 직후에는 급조향 감지 스킵
            if sample_initialized and prev_sample_time == curr_time:
                pass
            elif sample_initialized and not sudden_detected and angular_rate > SUDDEN_RATE_UP:
                sudden_alert = True
                sudden_detected = True
                last_move_time = curr_time
                last_angle = filtered_angle
                toggle_names = {-1: "LEFT", 0: "OFF", 1: "RIGHT"}
                toggle_label = toggle_names.get(toggle_state, "OFF")
                print(f"\n[위험] 급조향 감지! (속도: {angular_rate:.0f}°/s) | 토글: {toggle_label:<5}")
            elif sudden_detected and angular_rate < SUDDEN_RATE_DOWN:
                sudden_detected = False
            elif sudden_detected:
                last_move_time = curr_time
                last_angle = filtered_angle
            elif angle_diff > IDLE_THRESHOLD:
                last_move_time = curr_time
                last_angle = filtered_angle

            prev_sample_angle = filtered_angle
            prev_sample_time = curr_time

            idle_duration = curr_time - last_move_time
            if ENABLE_HANDS_OFF:
                hands_off_active = idle_duration >= DANGER_TIME
            else:
                hands_off_active = False

            toggle_names = {-1: "LEFT", 0: "OFF", 1: "RIGHT"}
            toggle_label = toggle_names.get(toggle_state, "OFF")

            if ENABLE_HANDS_OFF and hands_off_active:
                print(
                    f"[경고] {DANGER_TIME:.0f}초 무조작! 핸들을 잡으세요! | 토글: {toggle_label:<5}",
                    end='\r',
                    flush=True
                )
            else:
                print(
                    f"각도: {filtered_angle:6.2f}° | 속도: {angular_rate:6.1f}°/s | 무조작: {idle_duration:4.1f}초 | 토글: {toggle_label:<5}",
                    end='\r',
                    flush=True
                )
        else:
            sudden_detected = False
            hands_off_active = False
            idle_status_count = 0
            idle_duration = 0.0
        
        # 3. 심박수 (ADS1115 + Pulse Sensor)
        if heart_chan is not None:
            try:
                val = heart_chan.value
                samples.append(val)
                if len(samples) > 20: samples.pop(0)
                avg = sum(samples) / len(samples)
                
                # 간단한 피크 감지
                curr_time = time.time()
                if val > (avg + HEART_PEAK_DELTA) and (curr_time - last_beat_time) > 0.4:
                    new_bpm = 60 / (curr_time - last_beat_time)
                    # ✅ BPM을 바로 업데이트하지 말고 이전 값과 평균내기
                    if bpm > 0:
                        bpm = (bpm * 0.7 + new_bpm * 0.3)  # 스무딩
                    else:
                        bpm = new_bpm
                    last_beat_time = curr_time
                # ✅ 피크가 없어도 BPM은 유지 (0으로 리셋하지 않음)
                heart_debug_count += 1
                if heart_debug_count % 50 == 0:
                    # BPM raw 디버깅 메시지 제거
                    pass
            except Exception as e:
                print(f"⚠️ ADS1115 읽기 실패: {e}")
        else:
            if heart_debug_count % 200 == 0:
                print("⚠️ ADS1115 채널 없음: heart_chan is None")
            heart_debug_count += 1
        
        # 공유 변수 업데이트 (센서 데이터)
        shared.update_sensor(bpm, filtered_angle, idle_duration)

        # --- MQTT 심박 전송 (1초 주기) ---
        now_bpm_pub = time.time()
        if (now_bpm_pub - last_bpm_publish_time) >= 1.0:
            publish_heart_mqtt(int(bpm), "(CTRL)")
            last_bpm_publish_time = now_bpm_pub

        # ==================================
        # ⭐ 핵심: 멀티 모달 퓨전 경보 로직 ⭐
        # ==================================
        
        # 데이터 가져오기 (Lock 사용 권장되나 읽기는 간단히)
        d_level = shared.drowsy_level
        l_status = shared.lane_status

        # --- MQTT 상태 전송 (컨트롤 스레드 보강) ---
        now_pub = time.time()
        if d_level != last_published_state_ctrl or (now_pub - last_publish_time_ctrl) >= 1.0:
            if d_level != last_published_state_ctrl:
                    pass  # 상태 변경 시 아무 동작 없음
            if publish_state_mqtt(d_level, "(CTRL)"):
                last_published_state_ctrl = d_level
                last_publish_time_ctrl = now_pub
        
        warning_msg = []
        is_danger = False
        
        # 5단계 경고 시스템
        # LEVEL 0 NORMAL: 아무 경고 없음
        # LEVEL 1 CAUTION: 약한 진동 1회, 짧은 텍스트 알림
        # LEVEL 2 WARNING: 진동 3회, 부저 3회
        # LEVEL 3 DANGER: 진동/부저 반복
        # LEVEL 4 EMERGENCY: 진동/부저 빠른 반복
        if buzzer_vib_enabled:
            if d_level == 1:
                warning_msg.append("CAUTION")
                if vib_motor is not None:
                    vib_motor.on()
                    time.sleep(0.18)
                    vib_motor.off()
                if buzzer is not None:
                    buzzer.on()
                    time.sleep(0.18)
                    buzzer.off()
                publish_state_mqtt(1, "CAUTION")
            elif d_level == 2:
                warning_msg.append("WARNING")
                for _ in range(3):
                    if vib_motor is not None:
                        vib_motor.on()
                        time.sleep(0.22)
                        vib_motor.off()
                        time.sleep(0.12)
                for _ in range(3):
                    if buzzer is not None:
                        buzzer.on()
                        time.sleep(0.22)
                        buzzer.off()
                        time.sleep(0.12)
                publish_state_mqtt(2, "WARNING")
            elif d_level == 3:
                warning_msg.append("DANGER")
                for _ in range(4):
                    if buzzer is not None:
                        buzzer.on()
                    if vib_motor is not None:
                        vib_motor.on()
                    time.sleep(0.18)
                    if buzzer is not None:
                        buzzer.off()
                    if vib_motor is not None:
                        vib_motor.off()
                    time.sleep(0.10)
                publish_state_mqtt(3, "DANGER")
            elif d_level == 4:
                # EMERGENCY 경보 스레드 실행 (중복 방지)
                if not hasattr(run_control_logic, "emergency_thread") or run_control_logic.emergency_thread is None or not run_control_logic.emergency_thread.is_alive():
                    def last_move_time_ref():
                        return last_move_time
                    run_control_logic.emergency_thread = threading.Thread(target=play_emergency_pattern, args=(last_move_time_ref,), daemon=True)
                    run_control_logic.emergency_thread.start()
        # 차선이탈, 급조향, 핸들 무조작 등 기존 경고는 warning_msg에 추가
        if l_status == "DEPART":
            warning_msg.append("차선이탈")
        if sudden_alert:
            warning_msg.append("급조향")
        if hands_off_active:
            warning_msg.append("핸들 무조작")
        is_danger = d_level >= 2 or l_status == "DEPART" or sudden_alert or hands_off_active

        # 경보 실행 (EMERGENCY는 별도 스레드)
        if is_danger and buzzer_vib_enabled and d_level < 4:
            if not alert_active:
                unique_reasons = list(dict.fromkeys(warning_msg))
                print(f"\n🚨 위험 감지! 이유: {', '.join(unique_reasons)}")
                alert_active = True
            if buzzer is not None:
                buzzer.on()
            if vib_motor is not None:
                vib_motor.on()
            time.sleep(0.3)
            if buzzer is not None:
                buzzer.off()
            if vib_motor is not None:
                vib_motor.off()
            time.sleep(0.2)
        else:
            alert_active = False
        time.sleep(0.05)

# ==========================================
# 5.5. 디스플레이 스레드 (HDMI 출력)
# ==========================================
def run_display_thread():
    """HDMI 디스플레이에 얼굴 + 차선 인식 결과를 나란히 표시"""
    print("📺 디스플레이 스레드 시작 (DISPLAY=:0)")
    print(f"   현재 DISPLAY: {os.environ.get('DISPLAY', 'NOT SET')}")
    print(f"   현재 XAUTHORITY: {os.environ.get('XAUTHORITY', 'NOT SET')}")

    def resize_with_padding(img, target_w, target_h, pad_color=(0, 0, 0)):
        if img is None:
            return np.zeros((target_h, target_w, 3), dtype=np.uint8)
        h, w = img.shape[:2]
        if h == 0 or w == 0:
            return np.zeros((target_h, target_w, 3), dtype=np.uint8)
        scale = min(target_w / w, target_h / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        resized = cv2.resize(img, (new_w, new_h))
        canvas = np.full((target_h, target_w, 3), pad_color, dtype=np.uint8)
        x = (target_w - new_w) // 2
        y = (target_h - new_h) // 2
        canvas[y:y + new_h, x:x + new_w] = resized
        return canvas

    def get_screen_size():
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            w = root.winfo_screenwidth()
            h = root.winfo_screenheight()
            root.destroy()
            return w, h
        except Exception:
            return None, None

    def move_window_left_center(win_name, win_w, win_h, x_margin=0, y_offset=-80):
        scr_w, scr_h = get_screen_size()
        # 왼쪽 상단에서 50px 아래로 이동
        cv2.moveWindow(win_name, 0, 80)
    
    window_created = False
    no_frame_count = 0
    system_ready = False
    button_rect = None
    button_color = (0, 200, 0)
    button_text = "Launch System"
    button_clicked = False
    
    while shared.running:
        face_frame = None
        lane_frame = None
        bpm = 0
        
        with shared.lock:
            face_frame = shared.face_frame
            lane_frame = shared.lane_frame
            bpm = shared.bpm  # ✅ 심박수 가져오기
        
        # 두 프레임 모두 있으면 병렬로 표시
        if face_frame is not None and lane_frame is not None:
            try:
                # 1: 얼굴(왼쪽 전체), 2: 차선 카메라(오른쪽 위), 3: 차선(오른쪽 아래)
                # face_frame이 RGB라면 BGR로 변환
                if face_frame.shape[2] == 3:
                    face_bgr = cv2.cvtColor(face_frame, cv2.COLOR_RGB2BGR)
                else:
                    face_bgr = face_frame
                face_resized = cv2.resize(face_bgr, (640, 480))

                lane_h, lane_w = lane_frame.shape[:2]
                mid = lane_w // 2
                if mid > 0:
                    lane_cam = lane_frame[:, :mid]
                    lane_diag = lane_frame[:, mid:]
                else:
                    lane_cam = lane_frame
                    lane_diag = np.zeros_like(lane_cam)

                right_w = face_resized.shape[1]
                right_h = face_resized.shape[0]
                half_h = right_h // 2

                lane_cam_resized = resize_with_padding(lane_cam, right_w, half_h)
                lane_diag_resized = resize_with_padding(lane_diag, right_w, right_h - half_h)

                # ✅ face_resized에 심박수 표시
                cv2.putText(face_resized, f"BPM: {int(bpm)}", (20, right_h - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)  # STATE와 동일 두께

                # ✅ lane_cam_resized에 토글 스위치 상태 표시 (LEFT/OFF/RIGHT)
                toggle_names = {-1: "LEFT", 0: "OFF", 1: "RIGHT"}  # ✅ 특수문자 제거
                toggle_colors = {-1: (255, 165, 0), 0: (0, 0, 255), 1: (0, 165, 255)}  # 주황/빨강/청록
                toggle_status = toggle_names.get(shared.toggle_switch, "UNKNOWN")
                toggle_color = toggle_colors.get(shared.toggle_switch, (255, 255, 255))

                cv2.putText(lane_cam_resized, f"Turn Signal: {toggle_status}", (20, half_h - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, toggle_color, 3)

                right_col = np.vstack([lane_cam_resized, lane_diag_resized])
                combined = np.hstack([face_resized, right_col])

                # ===== 화면 해상도에 맞게 원본 비율 유지 리사이즈 (가로/세로 중 큰 쪽 기준) =====
                scr_w, scr_h = get_screen_size()
                if scr_w and scr_h:
                    h, w = combined.shape[:2]
                    scale = min(scr_w / w, scr_h / h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    combined_full = cv2.resize(combined, (new_w, new_h))
                else:
                    combined_full = combined

                if not window_created:
                    cv2.namedWindow(shared.display_window, cv2.WINDOW_AUTOSIZE)
                    move_window_left_center(shared.display_window, combined_full.shape[1], combined_full.shape[0])
                    window_created = True
                    print(f"✅ 윈도우 생성: {shared.display_window}")

                cv2.imshow(shared.display_window, combined_full)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("⏹️ 'q' 키로 시스템 종료")
                    shared.running = False
                    break
            except cv2.error as e:
                print(f"⚠️ OpenCV 디스플레이 에러: {e}")
                window_created = False
            except Exception as e:
                print(f"⚠️ 디스플레이 에러: {e}")
        # 한쪽만 있으면 그것만 표시
        elif face_frame is not None:
            try:
                if not window_created:
                    cv2.namedWindow(shared.display_window, cv2.WINDOW_AUTOSIZE)
                    move_window_left_center(shared.display_window, face_display.shape[1], face_display.shape[0])
                    window_created = True
                
                # ✅ face_frame에 심박수 표시
                face_display = face_frame.copy()
                cv2.putText(face_display, f"BPM: {int(bpm)}", (20, 450), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)  # STATE와 동일 두께
                
                cv2.imshow(shared.display_window, face_display)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    shared.running = False
                    break
            except Exception as e:
                print(f"⚠️ 디스플레이 에러: {e}")
        elif lane_frame is not None:
            try:
                if not window_created:
                    cv2.namedWindow(shared.display_window, cv2.WINDOW_AUTOSIZE)
                    move_window_left_center(shared.display_window, lane_frame.shape[1], lane_frame.shape[0])
                    window_created = True
                
                cv2.imshow(shared.display_window, lane_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    shared.running = False
                    break
            except Exception as e:
                print(f"⚠️ 디스플레이 에러: {e}")
        else:
            no_frame_count += 1
            if no_frame_count % 100 == 0:  # 매 100번 반복마다
                print(f"⚠️ 프레임 없음 ({no_frame_count}번) - face_frame={face_frame is not None}, lane_frame={lane_frame is not None}")
            time.sleep(0.01)
    
    try:
        cv2.destroyAllWindows()
    except:
        pass
    print("📺 디스플레이 스레드 종료")

# ==========================================
# 5.6 디스플레이 스레드 (카메라 피드를 JPEG로 저장 후 표시)
# ==========================================
def run_camera_display():
    """카메라 피드를 /tmp에 JPEG로 저장하고 fbi로 표시"""
    print("🎮 카메라 디스플레이 스레드 시작...")
    
    frame_count = 0
    
    while shared.running:
        frame = shared.get_display_frame()
        
        if frame is not None:
            try:                
                # 프레임을 JPEG로 저장
                temp_file = f"/tmp/camera_frame_{frame_count % 2}.jpg"
                cv2.imwrite(temp_file, frame)
                frame_count += 1
                time.sleep(0.03)  # ~30 FPS
            except Exception as e:
                pass
        else:
            time.sleep(0.01)
    
    print("🎮 카메라 디스플레이 종료")

# ==========================================
# 6. 메인 실행부
# ==========================================
if __name__ == "__main__":
    play_tts_korean("시스템 시작합니다. 정면을 10초간 주시해 주세요. EAR 보정을 진행합니다.")
    print("--- [졸음운전 통합 방지 시스템] 부팅 중 ---")

    # DISPLAY가 없으면 디스플레이 스레드 비활성화
    display_env = os.environ.get("DISPLAY")
    xauth_env = os.environ.get("XAUTHORITY")
    headless = os.environ.get("HEADLESS") == "1"
    ENABLE_DISPLAY = bool(display_env) and bool(xauth_env) and not headless
    print(f"✅ DISPLAY={display_env!r} XAUTHORITY={xauth_env!r} HEADLESS={headless}")
    if not ENABLE_DISPLAY:
        print("⚠️ 디스플레이 비활성화 (DISPLAY/XAUTHORITY 미설정 또는 HEADLESS=1)")
    
    # 스레드 생성
    t_face = threading.Thread(target=run_face_detection)
    t_lane = threading.Thread(target=run_lane_detection)
    t_ctrl = threading.Thread(target=run_control_logic)
    t_display = threading.Thread(target=run_display_thread)  # ✅ OpenCV 디스플레이
    
    # 스레드 시작
    t_face.start()  # ✅ 카메라 0: 얼굴 인식
    if ENABLE_LANE:
        t_lane.start()  # ✅ 차선 인식
    t_ctrl.start()
    if ENABLE_DISPLAY:
        t_display.start()
    
    def shutdown_all():
        print("\n🛑 시스템 종료 요청...")
        play_tts_korean("시스템 종료합니다.")
        time.sleep(2.5)  # TTS 음성 재생 시간만큼 대기 (필요시 조정)
        shared.running = False
        # 스레드 종료 대기
        t_face.join(timeout=5)  # 얼굴 인식 스레드 종료
        if ENABLE_LANE and t_lane.is_alive():
            t_lane.join(timeout=5)  # ✅ 차선 인식 스레드 종료
        t_ctrl.join(timeout=5)
        if ENABLE_DISPLAY and t_display.is_alive():
            t_display.join(timeout=2)
        # 하드웨어 안전 종료
        if buzzer is not None:
            buzzer.off()
        if vib_motor is not None:
            vib_motor.off()
        print("✅ 모든 시스템이 안전하게 종료되었습니다.")

    try:
        while shared.running:
            time.sleep(1)
            # 메인 스레드는 여기서 프로그램이 죽지 않게 대기
            # 추후 Node-RED 전송 로직 등을 여기에 넣어도 됨
        shutdown_all()
    except KeyboardInterrupt:
        shutdown_all()