# 위치 추정 모듈
# 맵 기반 LiDAR 매칭을 통한 로컬라이제이션
import os
import sys
import json
import numpy as np
from typing import Tuple, Optional

from config import ANGLE_STEP, MIN_DIST_MM


# 위치 추정 클래스
class Localizer:
    # 초기화
    def __init__(self, map_path: str):
        self.load_map(map_path)
        self.precompute_scans()
    
    # 맵 로드
    def load_map(self, path: str):
        if not os.path.exists(path):
            sys.exit(1)
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        self.width = data['width']
        self.height = data['height']
        self.res = data['resolution']
        self.grid = np.array(data['grid']).reshape((self.height, self.width))
        
        # 후보 위치 추출 (빈 공간)
        self.candidates_yx = np.argwhere(self.grid == 0)
    
    # 미리 계산된 스캔 데이터 생성
    def precompute_scans(self):
        # 0도 기준 가상 스캠 데이터 미리 계산
        self.virtual_scans = []
        check_angles = np.arange(0, 360, ANGLE_STEP)
        self.sin_table = np.sin(np.deg2rad(check_angles))
        self.cos_table = np.cos(np.deg2rad(check_angles))
        
        for y, x in self.candidates_yx:
            v_scan = self.simulate_lidar(x, y)
            self.virtual_scans.append({'yx': (y, x), 'scan': v_scan})
    
    # 특정 위치에서의 가상 LiDAR 스캔 시뮬레이션
    def simulate_lidar(self, start_x: int, start_y: int) -> np.ndarray:
        ranges = []
        for i in range(len(self.sin_table)):
            sin_a = self.sin_table[i]
            cos_a = self.cos_table[i]
            dist_step = 0
            
            while True:
                dist_step += 1
                curr_x = int(start_x + dist_step * cos_a)
                curr_y = int(start_y + dist_step * sin_a)
                
                # 맵 경계 체크
                if not (0 <= curr_x < self.width and 0 <= curr_y < self.height):
                    break
                
                # 장애물 체크
                if self.grid[curr_y][curr_x] == 1:
                    break
            
            ranges.append(dist_step * self.res)
        
        # 각도별 거리 배열 반환
        return np.array(ranges)
    
    # 위치 찾기
    def find_location(self, real_scan_vector: np.ndarray, current_angle_int: int) -> Tuple[Optional[Tuple[int, int]], float]:
        best_diff = float('inf')
        best_yx = None
        
        # 1. 배열 회전 (Data Rotation)
        # 각도만큼 데이터를 회전시켜 0도 기준으로 변환
        shift_idx = int(current_angle_int / ANGLE_STEP)
        rotated_scan = np.roll(real_scan_vector, shift_idx)
        
        # 2. 유효 데이터 마스킹
        valid_mask = rotated_scan > (MIN_DIST_MM / 1000.0)
        
        if np.sum(valid_mask) < 5:
            return None, 9999
        
        real_valid = rotated_scan[valid_mask]
        
        # 3. 전수 조사 (Brute-force matching)
        for cand in self.virtual_scans:
            sim_scan = cand['scan']
            sim_valid = sim_scan[valid_mask]
            
            # 거리 차이 계산
            diff = np.sum(np.abs(real_valid - sim_valid))
            avg_diff = diff / len(real_valid)
            
            if avg_diff < best_diff:
                best_diff = avg_diff
                best_yx = cand['yx']
        
        return best_yx, best_diff
