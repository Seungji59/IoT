# Socket.IO 클라이언트 모듈
# Flask 서버와의 실시간 통신
import socketio
from typing import Dict, Any

from config import SERVER_URL


# Socket.IO 클라이언트 래퍼 클래스
class SocketClient:
    # - 서버 연결 관리
    # - 데이터 전송(성공 여부 반환)
    
    # 초기화
    def __init__(self, server_url: str = SERVER_URL):
        self.server_url = server_url
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.is_connected = False
        
        # 이벤트 핸들러 등록
        self._setup_handlers()
    
    # 이벤트 핸들러 설정
    def _setup_handlers(self):
        @self.sio.event
        def connect():
            self.is_connected = True
        
        @self.sio.event
        def disconnect():
            self.is_connected = False
    
    # 서버 연결 시도
    def connect(self) -> bool:
        try:
            self.sio.connect(self.server_url)
            return True
        except Exception as e:
            return False
    
    # 서버 연결 해제
    def disconnect(self):        
        if self.is_connected:
            self.sio.disconnect()
    
    # 카트 상태 전송
    def send_state(self, x: float, y: float, angle: int) -> bool:
        if not self.is_connected:
            return False
        
        try:
            payload = {
                'x': x,
                'y': y,
                'angle': angle
            }
            self.sio.emit('update_full_state', payload)
            return True
        except Exception as e:
            return False
    
    # 커스텀 이벤트 전송
    def send_event(self, event_name: str, data: Dict[str, Any]) -> bool:
        if not self.is_connected:
            return False
        
        try:
            self.sio.emit(event_name, data)
            return True
        except Exception as e:
            return False
    
    # 도난 경고 알림 전송
    def send_theft_alert(self, confidence: int) -> bool:
        if not self.is_connected:
            return False
        
        try:
            payload = {
                'confidence': confidence
            }
            return self.send_event('update_confidence', payload)
        except Exception as e:
            return False
    
    
    # 연결 상태 확인
    @property
    def connected(self) -> bool:
        return self.is_connected
