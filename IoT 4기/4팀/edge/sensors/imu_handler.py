# IMU 센서 핸들러 모듈
# 자이로스코프를 사용한 각도 추적
import time
import threading
import numpy as np
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250

from config import (
    IMU_I2C_BUS,
    IMU_CALIBRATION_SAMPLES,
    IMU_UPDATE_RATE,
    IMU_DEADZONE_THRESHOLD,
    INITIAL_MAP_ANGLE_OFFSET
)


# IMUHandler 클래스 정의
class IMUHandler:
    def __init__(self):
        # IMU 초기화 및 보정
        self.lock = threading.Lock()
        self.running = False
        self.current_angle = 0.0
        
        try:
            self.mpu = MPU9250(
                address_ak=AK8963_ADDRESS,
                address_mpu_master=MPU9050_ADDRESS_68,
                bus=IMU_I2C_BUS,
                gfs=GFS_250,
                afs=AFS_2G,
                mfs=AK8963_BIT_16,
                mode=AK8963_MODE_C100HZ
            )
            self.mpu.configure()
            self.mpu.calibrateMPU6500()
            self.mpu.configure()
            self.mpu.writeMaster(INT_PIN_CFG, 0x02, 0.1)
            
            # 자이로 바이어스(평균 오차) 계산
            self.gyro_bias = self._calibrate_gyro()
            
        except Exception as e:
            self.mpu = None

    # 자이로 보정 메서드
    def _calibrate_gyro(self) -> float:
        bias = 0.0
        for _ in range(IMU_CALIBRATION_SAMPLES):
            bias += self.mpu.readGyroscopeMaster()[2]
            time.sleep(0.005)
        return bias / IMU_CALIBRATION_SAMPLES

    # 백그라운드 업데이트 스레드 시작 메서드
    def start(self):
        if self.mpu is None:
            return
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    # 업데이트 스레드 중지 메서드
    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()

    # 자이로 적분 업데이트 루프
    def _update_loop(self):
        cart_theta = 0.0
        last_time = time.perf_counter()
        
        while self.running:
            try:
                gyro = self.mpu.readGyroscopeMaster()
                current_time = time.perf_counter()
                dt = current_time - last_time
                last_time = current_time

                # Z축 회전량 읽기
                gz = gyro[2] - self.gyro_bias
                
                # 노이즈 제거 (Deadzone)
                if abs(gz) < IMU_DEADZONE_THRESHOLD:
                    gz = 0.0

                # 적분 (각도 누적)
                cart_theta += np.radians(gz * dt)
                deg = np.degrees(cart_theta) % 360
                
                with self.lock:
                    self.current_angle = deg
                
                time.sleep(IMU_UPDATE_RATE)
                
            except Exception as e:
                pass

    # 현재 각도 반환 메서드
    def get_angle_int(self) -> int:
        with self.lock:
            # 초기 오프셋 반영 및 360도 나머지 연산
            final_angle = (self.current_angle + INITIAL_MAP_ANGLE_OFFSET) % 360
            return int(final_angle)
