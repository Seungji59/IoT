# LiDAR 데이터 처리 모듈
import time
import numpy as np
from typing import List, Tuple
from rplidar import RPLidar

from config import ANGLE_STEP, NOISE_ANGLE_RANGES


# LiDAR 처리 클래스
class LidarProcessor:
    # 클래스 초기화
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.lidar = None
    
    # LiDAR 연결
    def connect(self):
        try:
            self.lidar = RPLidar(self.port, baudrate=self.baudrate)
            # 재연결 시퀀스
            self.lidar.stop()
            self.lidar.disconnect()
            time.sleep(1)
            self.lidar.connect()
        except Exception as e:
            self.lidar = None
    
    # LiDAR 연결 해제
    def disconnect(self):
        if self.lidar:
            try:
                self.lidar.stop()
                self.lidar.stop_motor()
                self.lidar.disconnect()
            except:
                pass
    
    # LiDAR 스캔 이터레이터
    def iter_scans(self):
        if self.lidar:
            return self.lidar.iter_scans()
        return iter([])
    
    # 정적 메서드: 노이즈 각도 판별
    @staticmethod
    def is_noise_angle(raw_angle: float) -> bool:
        for min_angle, max_angle in NOISE_ANGLE_RANGES:
            if min_angle <= raw_angle <= max_angle:
                return True
        return False
    
    # 정적 메서드: 스캔 데이터 처리
    @staticmethod
    def process_scan(scan_items: List[Tuple[int, float, float]]) -> np.ndarray:
        num_bins = 360 // ANGLE_STEP
        bins = np.zeros(num_bins)
        counts = np.zeros(num_bins)
        
        for (_, raw_angle, dist_mm) in scan_items:
            if dist_mm == 0:
                continue
            if LidarProcessor.is_noise_angle(raw_angle):
                continue
            
            # 각도 구간 인덱스 계산
            idx = int(raw_angle // ANGLE_STEP) % num_bins
            bins[idx] += (dist_mm / 1000.0)  # mm to m
            counts[idx] += 1
        
        # 평균 계산
        result_scan = np.zeros(num_bins)
        for i in range(num_bins):
            if counts[i] > 0:
                result_scan[i] = bins[i] / counts[i]
            else:
                result_scan[i] = 0.0
        
        return result_scan
