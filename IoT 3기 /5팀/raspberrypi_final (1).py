import os, time, warnings, signal, threading
from collections import deque, defaultdict
import numpy as np
import cv2
import torch
import paho.mqtt.client as mqtt
from deep_sort_realtime.deepsort_tracker import DeepSort
import board, busio, adafruit_vl53l0x

warnings.filterwarnings("ignore")
try: cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except: pass

# ===== BABY tracker MQTT =====
BROKER_BABY, PORT_BABY = "192.168.0.15", 1883
try:
    client_baby = mqtt.Client()
    client_baby.username_pw_set("tukorea", "tukorea123")
    client_baby.connect(BROKER_BABY, PORT_BABY, 60)
    client_baby.loop_start()
    BABY_OK = True
except Exception as e:
    print(f"[MQTT-BABY] Disabled: {e}")
    client_baby = None
    BABY_OK = False

def send_control(cmd):
    print(f"[CONTROL] {cmd}")
    if BABY_OK:
        try: client_baby.publish("robot/control", cmd)
        except: pass

def send_ir(val):
    if BABY_OK:
        try: client_baby.publish("robot/ir", str(val))
        except: pass


# ===== RISK detector MQTT =====
BROKER_RISK, PORT_RISK = "192.168.0.10", 1883
try:
    client_risk = mqtt.Client()
    client_risk.username_pw_set("tukorea", "tukorea123")
    client_risk.connect(BROKER_RISK, PORT_RISK, 60)
    client_risk.loop_start()
    RISK_OK = True
except Exception as e:
    print(f"[MQTT-RISK] Disabled: {e}")
    client_risk = None
    RISK_OK = False

def send_log(msg):
    print(f"[LOG] {msg}")
    if RISK_OK:
        try: client_risk.publish("robot/logs", msg)
        except: pass

def send_warning(msg):
    print(f"[WARN] {msg}")
    if RISK_OK:
        try: client_risk.publish("robot/warning", msg)
        except: pass


# ===== VL53L0X =====
i2c = busio.I2C(board.SCL, board.SDA)
vl53 = adafruit_vl53l0x.VL53L0X(i2c)
dist_mm = None
def range_loop():
    global dist_mm
    while True:
        try:
            dist_mm = int(vl53.range)
            send_ir(dist_mm)
        except:
            dist_mm = None
        time.sleep(0.1)
threading.Thread(target=range_loop, daemon=True).start()

# ===== 카메라 =====
CAM_INDEX, CAM_W, CAM_H, CAM_FPS = 0, 640, 480, 15
cap = cv2.VideoCapture(CAM_INDEX)
if not cap.isOpened():
    raise RuntimeError("❌ 카메라 열기 실패")
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
cap.set(cv2.CAP_PROP_FPS, CAM_FPS)

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or CAM_W

# ===== IOU Tracker (BABY) =====
class SimpleIOUTracker:
    def __init__(self, max_age=20, iou_thr=0.5):
        self.max_age, self.iou_thr = max_age, iou_thr
        self.next_id=1; self.tracks={}
    @staticmethod
    def iou(a,b):
        ax1,ay1,ax2,ay2=a; bx1,by1,bx2,by2=b
        ix1,iy1=max(ax1,bx1),max(ay1,by1); ix2,iy2=min(ax2,bx2),min(ay2,by2)
        iw,ih=max(0,ix2-ix1),max(0,iy2-iy1); inter=iw*ih
        if inter<=0: return 0.0
        area_a=(ax2-ax1)*(ay2-ax1); area_b=(bx2-bx1)*(by2-by1)
        return inter/(area_a+area_b-inter+1e-9)
    @staticmethod
    def xywh_to_xyxy(xywh):
        x,y,w,h=xywh; return [x,y,x+w,y+h]
    def update(self, detections):
        det_boxes=[self.xywh_to_xyxy(d[0]) for d in detections]
        used=[False]*len(det_boxes)
        for tid,tr in list(self.tracks.items()):
            best,bj=0.0,-1
            for j,db in enumerate(det_boxes):
                if used[j]: continue
                i=self.iou(tr['bbox'],db)
                if i>best: best=i; bj=j
            if best>=self.iou_thr and bj>=0:
                tr['bbox']=det_boxes[bj]; tr['miss']=0; used[bj]=True
            else:
                tr['miss']=tr.get('miss',0)+1
        for j,u in enumerate(used):
            if not u and j < len(det_boxes):
                self.tracks[self.next_id]={'bbox':det_boxes[j],'miss':0}
                self.next_id+=1
        for tid in list(self.tracks.keys()):
            if self.tracks[tid]['miss']>self.max_age:
                del self.tracks[tid]
        outs=[]
        for tid,tr in self.tracks.items():
            x1,y1,x2,y2=tr['bbox']; outs.append({'track_id':tid,'ltrb':(x1,y1,x2,y2)})
        return outs

baby_tracker = SimpleIOUTracker(max_age=20, iou_thr=0.5)
cx_history = deque(maxlen=5)

# ===== 위험 객체 설정 =====
LEVEL3 = {"knife","scissors","fork","bottle","microwave"}
LEVEL2 = {"cup","bowl","tv","refrigerator","chair","dining table","couch","bed",
          "potted plant","sink","baseball bat","skateboard","sports ball","tennis racket"}
LEVEL1 = {"cell phone","remote","mouse","keyboard","laptop","book",
          "backpack","handbag","suitcase","umbrella","teddy bear"}
def risk_level(name: str) -> int:
    if name in LEVEL3: return 3
    if name in LEVEL2: return 2
    if name in LEVEL1: return 1
    return 0

COLORS = {3:(0,0,255), 2:(0,128,255), 1:(0,255,255)}

# ===== YOLO =====
model = torch.hub.load("ultralytics/yolov5", "yolov5n", pretrained=True)
model.eval()

# ===== DeepSort (위험 객체) =====
ds_tracker = DeepSort(max_age=10, n_init=2, max_iou_distance=0.7, embedder="mobilenet")

# ===== BABY 선택 =====
def choose_baby(tracks, prev_bbox, frame_w):
    if not tracks: return None
    if prev_bbox is not None:
        best_iou, best_tid = 0, None
        for tr in tracks:
            i = SimpleIOUTracker.iou(prev_bbox, tr['ltrb'])
            if i > best_iou: best_iou, best_tid = i, tr['track_id']
        if best_iou > 0.3: return best_tid
    center_x = frame_w//2
    best_dist, best_tid = 1e9, None
    for tr in tracks:
        x1,y1,x2,y2 = tr['ltrb']
        cx = (x1+x2)//2
        dist = abs(cx-center_x)
        if dist < best_dist: best_dist, best_tid = dist, tr['track_id']
    return best_tid

# ===== 메인 루프 =====
CENTER_THRESHOLD, STRONG_MULTIPLIER = 80, 2.0
last_sent_time, last_cmd, baby_id = 0.0, None, None
baby_tracker.last_baby_bbox = None

# 위험물 중복 방지
last_sent = defaultdict(float)
COOLDOWN = 2.0  # 초 단위

try:
    while True:
        ok, frame = cap.read()
        if not ok: continue

        results = model(frame, size=320)
        dets=[]
        for *box, conf, cls in results.xyxy[0]:
            x1,y1,x2,y2 = map(int, box)
            name = model.names[int(cls)]
            dets.append(([x1,y1,x2-x1,y2-y1], float(conf.item()), name))

    
        # ===== 위험 객체 처리 =====
        ds_inputs=[d for d in dets if risk_level(d[2])>0]
        tracks_risk = ds_tracker.update_tracks(ds_inputs, frame=frame)

        for t in tracks_risk:
            if not t.is_confirmed():  # 확인된 트랙만 사용
                continue
            name = t.get_det_class() or "object"
            lvl = risk_level(name)
            if lvl >= 1:
                x1,y1,x2,y2 = map(int, t.to_ltrb())
                color = COLORS.get(lvl, (255,128,0))
                cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
                cv2.putText(frame,f"{name} L{lvl}",(x1,max(0,y1-6)),
                            cv2.FONT_HERSHEY_SIMPLEX,0.6,color,2)

                # 메시지 포맷
                tag = "[NOTICE]" if lvl==1 else "[OBSERVE]" if lvl==2 else "[WARNING]"
                msg = f"{tag} {name} LEVEL {lvl}"

                # 중복 방지 (쿨다운 적용)
                now = time.time()
                key = f"{name}_L{lvl}"
                if now - last_sent[key] > COOLDOWN:
                    if lvl == 3:
                        send_warning(msg)
                    else:
                        send_log(msg)
                    last_sent[key] = now


        # ===== BABY 추적 처리 =====
        dets_person=[d for d in dets if d[2]=="person"]
        tracks_person=baby_tracker.update(dets_person)

        baby_seen=False
        if baby_id is None or not any(tr['track_id']==baby_id for tr in tracks_person):
            baby_id = choose_baby(tracks_person, baby_tracker.last_baby_bbox, frame_width)

        desired_cmd=None
        for tr in tracks_person:
            tid=tr['track_id']
            x1,y1,x2,y2=map(int,tr['ltrb'])
            cx=(x1+x2)//2
            if tid==baby_id:
                baby_seen=True
                baby_tracker.last_baby_bbox=(x1,y1,x2,y2)
                cx_history.append(cx)
                avg_cx=sum(cx_history)/len(cx_history)
                offset=avg_cx-frame_width//2
                if abs(offset)<=CENTER_THRESHOLD:
                    desired_cmd="CENTER"
                elif abs(offset)<=CENTER_THRESHOLD*STRONG_MULTIPLIER:
                    desired_cmd="SOFT_LEFT" if offset<0 else "SOFT_RIGHT"
                else:
                    desired_cmd="HARD_LEFT" if offset<0 else "HARD_RIGHT"

                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
                cv2.putText(frame,"BABY",(x1,y1-10),
                            cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)

        if not baby_seen:
            desired_cmd="STOP"

        now=time.time()
        if desired_cmd and (now-last_sent_time)>=1.0:
            if desired_cmd!=last_cmd:
                send_control(desired_cmd); last_cmd=desired_cmd; last_sent_time=now

        # ===== 화면 표시 =====
        if dist_mm is not None:
            cv2.putText(frame, f"Dist: {dist_mm}mm", (6,18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,255), 2)

        cv2.imshow("Unified Tracker", frame)
        if cv2.waitKey(1)&0xFF==ord('q'):
            break

finally:
    cap.release(); cv2.destroyAllWindows()
    client_baby.loop_stop(); client_baby.disconnect()
    client_risk.loop_stop(); client_risk.disconnect()
