# LiDAR와 IMU를 사용한 실시간 로컬라이제이션 시스템
from config import MAP_FILE, LIDAR_PORT, LIDAR_BAUDRATE, ENABLE_SERVER_COMMUNICATION
from sensors import IMUHandler, LidarProcessor
from localization import Localizer
from communication import SocketClient
from utils import calculate_confidence_score, format_coordinates, print_status, is_confident


class CartLocalizationSystem:
    # 카트 위치 추적 시스템 메인 클래스
    
    # 시스템 초기화
    def __init__(self):        
        # 1. IMU 센서 초기화 및 시작
        self.imu = IMUHandler()
        self.imu.start()
        
        # 2. 로컬라이저 초기화
        self.localizer = Localizer(MAP_FILE)
        
        # 3. LiDAR 초기화
        self.lidar = LidarProcessor(LIDAR_PORT, LIDAR_BAUDRATE)
        self.lidar.connect()
        
        # 4. 서버 클라이언트 초기화 (선택적)
        if ENABLE_SERVER_COMMUNICATION:
            self.socket_client = SocketClient()
            self.socket_client.connect()
        else:
            self.socket_client = None
    
    # 메인 루프 실행
    def run(self):        
        try:
            # 초기 몇 스캔 스킵 (안정화)
            scan_count = 0
            
            for scan in self.lidar.iter_scans():
                scan_count += 1
                if scan_count < 3:
                    continue
                
                self._process_scan(scan)
                
        except KeyboardInterrupt:
            pass
        except Exception as e:
            pass
        finally:
            self.cleanup()
    
    # 단일 스캔 처리
    def _process_scan(self, scan):
        # 1. 현재 각도 읽기
        current_angle = self.imu.get_angle_int()
        
        # 2. LiDAR 스캔 데이터 처리
        scan_vector = LidarProcessor.process_scan(scan)
        
        # 3. 위치 찾기
        best_yx, error = self.localizer.find_location(scan_vector, current_angle)
        
        if best_yx is not None:
            self._handle_location_found(best_yx, error, current_angle)
        else:
            pass
    
    # 위치 발견 후 처리
    def _handle_location_found(self, position_yx, error, angle):
        gy, gx = position_yx
        
        # 신뢰도 계산
        confidence = calculate_confidence_score(error)
        
        # 좌표 변환 및 포맷팅
        x_meter, y_meter = format_coordinates(gx, gy)
        
        # 서버로 전송 (활성화된 경우만)
        if self.socket_client is not None and self.socket_client.is_connected:
            
            # 도난 알림 전송 (신뢰도 임계값 이하)
            if not is_confident(error):
                self.socket_client.send_theft_alert(confidence)
                
            self.socket_client.send_state(x_meter, y_meter, angle)
    
    # 시스템 정리 및 종료
    def cleanup(self):        
        # IMU 정지
        self.imu.stop()
        
        # LiDAR 정리
        self.lidar.disconnect()
        
        # 서버 연결 해제 (활성화된 경우만)
        if self.socket_client is not None and self.socket_client.is_connected:
            self.socket_client.disconnect()