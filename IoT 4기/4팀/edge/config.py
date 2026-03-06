# 프로젝트 전역 설정 및 상수

# 서버 설정
ENABLE_SERVER_COMMUNICATION = True  # False로 변경하면 서버 통신 비활성화
SERVER_URL = 'http://192.168.0.10:8000'  # 서버 IP 주소. 디폴트: 192.168.0.10:8000

# 하드웨어 설정

# LiDAR 설정
LIDAR_PORT = '/dev/ttyUSB0'
LIDAR_BAUDRATE = 115200

# IMU 설정
IMU_I2C_BUS = 1
IMU_CALIBRATION_SAMPLES = 200
IMU_UPDATE_RATE = 0.005  # 200Hz
IMU_DEADZONE_THRESHOLD = 0.5  # 자이로 노이즈 제거 임계값 (deg/s)

# 맵 설정
MAP_FILE = 'localization/occupancy_grid_2d.json'

# 로컬라이제이션 설정
ANGLE_STEP = 2  # 각도 스텝 (도 단위)
MIN_DIST_MM = 200  # 최소 거리 (mm) - 노이즈 필터링
INITIAL_MAP_ANGLE_OFFSET = 0  # 초기 맵 각도 오프셋

# 위치 추정 신뢰도 임계값
CONFIDENCE_THRESHOLD = 7  # 신뢰도 점수 (0-10)

# 노이즈 각도 범위 (하드웨어 특성)
NOISE_ANGLE_RANGES = [
    (126, 138),
    (148, 212),
    (222, 234)
]
