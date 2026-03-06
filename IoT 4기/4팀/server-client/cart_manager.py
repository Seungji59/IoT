# cart_manager.py
import time
from config import Config

class CartManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.cart_id = self.db.get_next_cart_id()
        
        self.state = {'x': 0.0, 'y': 0.0, 'angle': 0}
        self.last_risk_time = 0.0

    def restart_shopping(self):
        # 쇼핑 재시작 및 ID 증가
        self.cart_id += 1

    def handle_risk(self):
        # 도난 발생 처리
        self.last_risk_time = time.time()

    def is_risk_active(self):
        # 현재 도난 차단 시간인지 확인
        return (time.time() - self.last_risk_time) < Config.RISK_TIMEOUT

    def update_state(self, data):
        # 상태 업데이트 및 DB 저장 판단
        # 1. 도난 상태 체크
        if self.is_risk_active():
            return False  # 업데이트/저장 중단

        # 2. 데이터 파싱 및 업데이트
        self.state['x'] = float(data.get('x', self.state['x']))
        self.state['y'] = float(data.get('y', self.state['y']))
        self.state['angle'] = int(data.get('angle', self.state['angle']))

        # 3. 제외 구역 체크
        x, y = self.state['x'], self.state['y']
        # (Start: 0.0~1.2, End: 0.0~1.2 로직에 따라 단순화)
        # 원본 코드 로직: (0.0 <= x <= 1.2) and (0.0 <= y <= 1.2)
        if (0.0 <= x <= 1.2) and (0.0 <= y <= 1.2):
            # 화면 갱신은 해야 하므로 True 반환, 단 save_db는 외부에서 호출 안하게 설계 가능
            # 여기서는 편의상 DB 저장만 스킵하기 위해 별도 처리
            return True 

        # 4. DB 저장
        self.db.save_cart_state(self.cart_id, self.state)
        return True

    def get_state(self):
        return self.state