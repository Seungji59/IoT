import os
import sys
import time
import cv2
import socketio
from picamera2 import Picamera2
from ultralytics import YOLO

# ==========================================
# ⚙️ 설정
# ==========================================
os.environ["OPENCV_LOG_LEVEL"] = "OFF"

SERVER_IP = 'http://192.168.0.10:8000'

YOLO_CONF = 0.5      # 확실한 것만 잡기 위해 신뢰도 약간 상향
IMG_SIZE = 640
DIFF_THRESHOLD = 20
DIFF_AREA_MIN = 1000
YOLO_INTERVAL = 1.0  # 분석 주기 (초)

# 🎯 허용된 물체 목록
ALLOWED_ITEMS = {'scissors', 'remote', 'mouse'}

# 소켓 클라이언트
sio = socketio.Client()

def connect_socket():
    try:
        if not sio.connected:
            sio.connect(SERVER_IP)
            print(f"✅ 소켓 서버 연결 성공: {SERVER_IP}")
    except Exception as e:
        print(f"⚠️ 소켓 연결 실패: {e}")

def find_model_path(name):
    paths = [f"./{name}", f"{os.path.expanduser('~')}/Desktop/{name}"]
    for p in paths:
        if os.path.exists(p): return p
    return None

def load_model():
    p_v11 = find_model_path("yolo11n_ncnn_model")
    if p_v11:
        print(f"✅ 모델 로드 성공: {p_v11}")
        return YOLO(p_v11, task="detect")
    raise FileNotFoundError("❌ 모델 폴더를 찾을 수 없습니다.")

def send_to_server(item_name):
    if item_name:
        print(f"📡 [서버 전송] '{item_name}' 전송 완료 (중복 방지 처리됨)")
        try:
            if not sio.connected:
                connect_socket()
            sio.emit('update_item', {'item_name': item_name})
        except Exception as e:
            print(f"❌ 전송 실패: {e}")

def main():
    connect_socket()

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": "BGR888", "size": (640, 480)})
    picam2.configure(config)
    picam2.start()
    print("📷 카메라 가동 시작...")

    model = load_model()
    time.sleep(2)
    baseline_frame = cv2.cvtColor(picam2.capture_array(), cv2.COLOR_RGB2BGR).copy()

    # ==========================================
    # 🛡️ 핵심: 이미 보낸 물품 목록 (집합)
    # ==========================================
    sent_items = set() 
    
    last_yolo_time = 0

    try:
        while True:
            # --- 모든 물품을 다 찾았으면 루프 종료 가능 (선택 사항) ---
            # if len(sent_items) == len(ALLOWED_ITEMS):
            #     print("🎉 모든 물품 감지 완료! 프로그램을 종료합니다.")
            #     break

            # 1. 캡처 & 움직임 감지
            frame_rgb = picam2.capture_array()
            curr_frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            gray_curr = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
            gray_base = cv2.cvtColor(baseline_frame, cv2.COLOR_BGR2GRAY)
            frame_diff = cv2.absdiff(gray_base, gray_curr)
            _, thresh = cv2.threshold(frame_diff, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
            diff_pixels = cv2.countNonZero(thresh)

            current_time = time.time()

            # 2. 움직임 있고 + 쿨타임 지남
            if diff_pixels > DIFF_AREA_MIN and (current_time - last_yolo_time > YOLO_INTERVAL):
                
                results = model.predict(curr_frame, imgsz=IMG_SIZE, conf=YOLO_CONF, verbose=False)
                last_yolo_time = current_time

                if results and results[0].boxes:
                    # 이번 프레임에서 가장 확실한 물건 하나 찾기
                    best_item = None
                    best_conf = 0

                    for box in results[0].boxes:
                        class_idx = int(box.cls[0])
                        class_name = results[0].names[class_idx]
                        conf = float(box.conf[0])

                        # 1. 허용된 물건인가? AND
                        # 2. 이미 보낸 물건이 아닌가? (⭐️ 핵심 조건)
                        if (class_name in ALLOWED_ITEMS) and (class_name not in sent_items):
                            if conf > best_conf:
                                best_conf = conf
                                best_item = class_name
                    
                    # 3. 새로운 물건이 발견되었다면?
                    if best_item:
                        # 서버로 전송
                        send_to_server(best_item)
                        
                        # [중요] 보낸 목록에 추가 -> 이제 영원히 다시 전송 안 함
                        sent_items.add(best_item)
                        
                        print(f"🔒 [Lock] '{best_item}' 등록됨. 현재 보낸 목록: {sent_items}")

            # 배경 갱신
            baseline_frame = curr_frame.copy()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n🛑 프로그램 종료")
        if sio.connected:
            sio.disconnect()
    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")
    finally:
        picam2.stop()

if __name__ == "__main__":
    main()