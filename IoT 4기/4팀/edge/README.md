# 카트 위치 추적 시스템

LiDAR와 IMU 센서를 사용한 실시간 로컬라이제이션 시스템

## 📁 프로젝트 구조

```
ws_final/
├── main.py                          # 메인 진입점 - 카트 로컬라이제이션 시스템
├── config.py                        # 전역 설정 및 상수
├── requirements.txt                 # Python 패키지 의존성
├── README.md                        # 프로젝트 문서
│
├── sensors/                         # 센서 관련 모듈
│   ├── __init__.py
│   ├── imu_handler.py              # IMU 센서 처리 (MPU9250)
│   └── lidar_processor.py          # LiDAR 데이터 처리 (RPLiDAR)
│
├── localization/                    # 위치 추정 모듈
│   ├── __init__.py
│   ├── localizer.py                # 맵 기반 위치 추정
│   └── occupancy_grid_2d.json      # 2D Occupancy Grid 맵 데이터
│
├── communication/                   # 통신 모듈
│   ├── __init__.py
│   └── socket_client.py            # Socket.IO 클라이언트 (서버 통신)
│
└── utils/                           # 유틸리티 모듈
    ├── __init__.py
    └── helpers.py                  # 헬퍼 함수들
```

## 🚀 사용법

### 1. 실행

```bash
python3 main.py
```

### 2. 설정 변경

`config.py` 파일에서 다음 항목들을 수정할 수 있습니다:

**서버 설정:**
- **ENABLE_SERVER_COMMUNICATION**: 서버 통신 활성화 여부 (기본: False)
- **SERVER_URL**: Flask 서버 주소

**하드웨어 설정:**
- **LIDAR_PORT**: LiDAR 시리얼 포트 (기본: '/dev/ttyUSB0')
- **LIDAR_BAUDRATE**: LiDAR 통신 속도 (기본: 115200)
- **IMU_I2C_BUS**: IMU I2C 버스 번호

**로컬라이제이션 설정:**
- **ANGLE_STEP**: 각도 스텝 (단위: 도, 기본: 2°) - 작을수록 정확하지만 계산량 증가
- **MIN_DIST_MM**: 최소 유효 거리 (기본: 200mm, 이하는 노이즈로 필터링)
- **INITIAL_MAP_ANGLE_OFFSET**: 초기 맵 각도 오프셋 (기본: 0°)
- **NOISE_ANGLE_RANGES**: 하드웨어 노이즈 각도 범위 (기본: 126-138°, 148-212°, 222-234°)

**신뢰도 & IMU 설정:**
- **CONFIDENCE_THRESHOLD**: 위치 추정 신뢰도 임계값 (기본: 7, 범위: 0-10)
- **IMU_CALIBRATION_SAMPLES**: IMU 보정 샘플 수 (기본: 200)
- **IMU_UPDATE_RATE**: IMU 업데이트 주기 (기본: 0.005초, 200Hz)
- **IMU_DEADZONE_THRESHOLD**: 자이로 노이즈 제거 임계값 (기본: 0.5)
- **THEFT_CONFIDENCE_THRESHOLD**: 도난 경고 임계값 (기본: 5, 이하시 도난 의심)

## 📦 모듈 설명

### sensors/
**IMUHandler** - MPU9250 자이로스코프 센서를 사용한 실시간 각도 추적
- 센서로부터 자이로스코프 각속도 데이터 읽기
- 각속도 적분을 통한 현재 각도 계산
- 바이어스 자동 보정 (시작 시 3초 캘리브레이션)
- 200Hz 주기로 실시간 각도 업데이트
- 데이터 동기화를 위한 스레드 안전 처리

**LidarProcessor** - RPLiDAR 스캔 데이터 처리
- RPLiDAR A1 센서와의 시리얼 통신
- 각도별 거리 데이터 수집 및 필터링
- 하드웨어 노이즈 범위 자동 제외
- 설정된 ANGLE_STEP에 따라 각도 구간별 평균 거리 계산
- 최소 거리(200mm) 이하는 노이즈로 제거

### localization/
**Localizer** - 2D 맵과 실시간 LiDAR 스캔을 매칭하여 위치 추정
- JSON 형식의 Occupancy Grid 맵 로드
- 맵의 모든 유효 셀에서 가상 LiDAR 스캔 데이터 미리 계산
- 실제 스캔과 가상 스캔의 각도별 거리 오차 계산
- 오차가 최소인 위치를 추정 위치로 선정
- 위치 추정의 정확도를 신뢰도 점수로 제공 (0-10)

### communication/
**SocketClient** - Socket.IO 기반 서버 통신
- Flask 서버와의 실시간 양방향 통신
- 카트의 현재 위치(x, y), 각도, 신뢰도 점수 전송
- 서버 연결 상태 모니터링 및 자동 재연결
- 신뢰도가 낮을 경우 도난 경고 메시지 전송

### utils/
**helpers** - 위치 추정 지원 함수들
- `calculate_confidence_score(error)`: 평균 오차(m)를 신뢰도 점수(0-10)로 변환 (공식: 최대(0, 10-error*3))
- `is_confident(error)`: 신뢰도가 CONFIDENCE_THRESHOLD 이상인지 판별
- `format_coordinates(grid_x, grid_y, resolution)`: 그리드 좌표를 미터 단위로 변환 (해상도 기본값: 0.1m)
- `print_status(timestamp, x, y, angle, confidence, warning)`: 카트 상태를 포맷팅하여 출력

---

## 🔬 핵심 알고리즘 상세 설명

### 1. IMU 기반 각도 추적 알고리즘

#### 자이로스코프 적분 방식
MPU9250 센서의 Z축 자이로스코프를 사용하여 카트의 회전 각도를 추적합니다.

**보정 과정 (Calibration):**
```
bias = (1 / N) × Σ(gz_i)  (i = 1 to N)
```
- 시작 시 200개 샘플의 자이로 데이터를 수집하여 평균 bias 계산
- 이후 모든 측정값에서 bias를 제거하여 드리프트 최소화

**각도 계산 (각속도 적분):**
```
θ(t) = θ(t-1) + ∫(ω_z - bias) dt
     ≈ θ(t-1) + (ω_z - bias) × Δt
```
- `ω_z`: Z축 각속도 (deg/s)
- `Δt`: 샘플링 주기 (0.005초 = 200Hz)
- `θ(t)`: 누적 각도 (0-360도로 정규화)

**노이즈 제거 (Deadzone Filtering):**
```
if |ω_z - bias| < threshold:
    ω_z_filtered = 0
```
- 임계값 이하의 미세한 각속도는 0으로 처리하여 드리프트 억제

#### 스레드 안전성
- 별도 데몬 스레드에서 200Hz 주기로 각도를 업데이트
- `threading.Lock()`을 사용한 동기화로 메인 루프와 데이터 충돌 방지

---

### 2. LiDAR 스캔 데이터 처리 파이프라인

#### 단계별 처리 과정

**Step 1: 원시 데이터 수집**
- RPLiDAR에서 각도-거리 쌍 데이터 수집: `[(quality, angle, distance), ...]`
- 360도 전체 회전 스캔 데이터를 1개 배치로 처리

**Step 2: 노이즈 필터링**
```python
# 하드웨어 노이즈 각도 제거
if angle in NOISE_ANGLE_RANGES:
    skip

# 최소 거리 이하 제거
if distance_mm < MIN_DIST_MM:
    skip
```

**Step 3: 각도 구간화 (Binning)**
```
bin_index = floor(angle / ANGLE_STEP) mod (360 / ANGLE_STEP)
```
- ANGLE_STEP=2°인 경우, 360° → 180개 구간으로 나눔
- 각 구간에 해당하는 거리 데이터를 누적

**Step 4: 구간별 평균 계산**
```
distance_avg[i] = (Σ distances in bin[i]) / count[i]
```
- 각 구간에 여러 측정값이 있는 경우 평균을 계산하여 노이즈 감소
- 측정값이 없는 구간은 0으로 설정

**출력 형식:**
- NumPy 배열 형태: `[d₀, d₁, d₂, ..., d₁₇₉]` (미터 단위)
- 길이 = 360 / ANGLE_STEP

---

### 3. 위치 추정 알고리즘 (Scan Matching)

본 시스템은 **Grid-based Brute-force Scan Matching** 방식을 사용합니다.

#### 3.1 전처리 단계 (Precomputation)

**맵 로드 및 파싱:**
```json
{
  "width": 300,
  "height": 300,
  "resolution": 0.1,
  "grid": [0, 0, 1, 0, ...] // 0=자유공간, 1=장애물
}
```

**후보 위치 추출:**
```python
candidates = {(y, x) | grid[y][x] == 0}
```
- 자유 공간(grid=0) 셀만 유효한 위치 후보로 추출

**가상 스캔 생성 (Ray Casting):**
맵의 각 후보 위치에서 0도 기준으로 가상 LiDAR 스캔을 시뮬레이션:
```
for each angle θ in [0°, 2°, 4°, ..., 358°]:
    distance = ray_cast(x, y, θ)
    virtual_scan[θ / ANGLE_STEP] = distance
```

**Ray Casting 알고리즘:**
```python
def ray_cast(x_start, y_start, θ):
    step = 0
    while True:
        step += 1
        x_curr = x_start + step × cos(θ)
        y_curr = y_start + step × sin(θ)
        
        if out_of_bounds(x_curr, y_curr):
            break
        if grid[y_curr][x_curr] == 1:  # 장애물
            break
    
    return step × resolution
```

- 각 각도 방향으로 광선을 발사하여 장애물까지의 거리 계산
- 삼각함수 테이블(`sin_table`, `cos_table`)을 미리 계산하여 속도 향상

#### 3.2 실시간 매칭 단계

**Step 1: 데이터 회전 (Rotation Compensation)**
```python
shift_idx = current_angle / ANGLE_STEP
rotated_scan = np.roll(real_scan_vector, shift_idx)
```
- IMU로부터 얻은 현재 각도만큼 스캔 데이터를 회전
- 카트가 회전한 상태에서도 맵의 0도 기준과 정렬

**예시:**
- 카트가 90도 회전한 상태
- 실제 스캔의 0도 방향 = 맵의 90도 방향
- `np.roll`로 데이터를 45개 인덱스(90/2) 이동하여 보정

**Step 2: 유효 데이터 마스킹**
```python
valid_mask = (rotated_scan > MIN_DIST_MM / 1000.0)
real_valid = rotated_scan[valid_mask]
```
- 유효한 측정값만 선택 (0이 아니고 최소 거리 이상)
- 유효 데이터가 5개 미만이면 매칭 실패 처리

**Step 3: 전수 조사 (Brute-force Search)**
```python
for each candidate_position in all_candidates:
    virtual_scan = precomputed_scans[candidate_position]
    virtual_valid = virtual_scan[valid_mask]
    
    # L1 거리 (맨해튼 거리) 계산
    diff = Σ |real_valid[i] - virtual_valid[i]|
    avg_error = diff / len(real_valid)
    
    if avg_error < best_error:
        best_error = avg_error
        best_position = candidate_position
```

**오차 계산 방식:**
- **L1 Norm (Manhattan Distance)** 사용
- 각 각도별 거리 차이의 절댓값 합을 계산
- 평균 오차 = 총 오차 / 유효 데이터 개수

**Step 4: 신뢰도 평가**
```python
confidence_score = max(0, 10 - avg_error × 3)
```
- 평균 오차가 작을수록 높은 신뢰도
- 0.33m 오차 = 9점, 1.0m 오차 = 7점, 3.33m 오차 = 0점

#### 알고리즘 복잡도
- **시간 복잡도**: O(N × M)
  - N = 후보 위치 개수
  - M = 각도 구간 개수 (180개)
- **공간 복잡도**: O(N × M) - 가상 스캔 데이터 저장
- **최적화**: 전처리를 통해 실시간 계산량 최소화

---

### 4. 전체 시스템 연산 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                        시스템 초기화                            │
├─────────────────────────────────────────────────────────────────┤
│ 1. IMU 센서 초기화 및 3초 캘리브레이션                          │
│ 2. 맵 로드 및 가상 스캔 데이터 전처리 (수천 개 위치)            │
│ 3. LiDAR 센서 연결 및 모터 시작                                 │
│ 4. Socket.IO 서버 연결 (선택적)                                 │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      메인 루프 (무한 반복)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐                         │
│  │   IMU 스레드 │      │  LiDAR 스캔  │                         │
│  │   (200Hz)    │      │   (5-10Hz)   │                         │
│  │              │      │              │                         │
│  │ θ(t) = θ(t-1)│      │ scan_data =  │                         │
│  │  + ω_z × Δt  │      │ [(θ,d), ...] │                         │
│  └──────┬───────┘      └──────┬───────┘                         │
│         │                     │                                 │
│         ↓                     ↓                                 │
│  ┌─────────────────────────────────────┐                        │
│  │   스캔 처리 (process_scan)          │                        │
│  │  • 노이즈 필터링                    │                        │
│  │  • 각도 구간화 및 평균 계산         │                        │
│  │  → scan_vector [d₀, d₁, ..., d₁₇₉]  │                        │
│  └─────────────┬───────────────────────┘                        │
│                │                                                │
│                ↓                                                │
│  ┌─────────────────────────────────────┐                        │
│  │   위치 추정 (find_location)         │                        │
│  │  1. 스캔 데이터 회전 (IMU 각도 반영)│                        │
│  │  2. 유효 데이터 마스킹              │                        │
│  │  3. 전수 조사로 최적 위치 탐색      │                        │
│  │  → (x, y), error                    │                        │
│  └─────────────┬───────────────────────┘                        │
│                │                                                │
│                ↓                                                │
│  ┌─────────────────────────────────────┐                        │
│  │   결과 처리                         │                        │
│  │  • 신뢰도 점수 계산                 │                        │
│  │  • 좌표 변환 (그리드 → 미터)        │                        │
│  │  • 콘솔 출력                        │                        │
│  │  • 서버 전송 (활성화 시)            │                        │
│  │  • 도난 경고 (신뢰도 낮을 시)       │                        │
│  └─────────────────────────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 데이터 흐름 상세

**1. 센서 데이터 수집:**
```
IMU (200Hz) → angular_velocity_z → θ_cart
LiDAR (~7Hz) → [(θ₁,d₁), (θ₂,d₂), ...] → scan_vector
```

**2. 좌표계 변환:**
```
LiDAR 좌표계 (카트 기준) → 회전 → 맵 좌표계 (0도=오른쪽)
np.roll(scan_vector, θ_cart / ANGLE_STEP)
```

**3. 위치 추정:**
```
scan_vector + θ_cart → Scan Matching → (grid_x, grid_y) → (x_meter, y_meter)
```

**4. 출력:**
```
(x, y, θ, confidence) → 콘솔
(x, y, θ), confidence(도난 의심 경보) → flask 서버
```

---

### 5. 주요 파라미터 영향 분석

| 파라미터 | 값 | 영향 |
|---------|-----|------|
| `ANGLE_STEP` | 2° | 작을수록 정밀하지만 계산량 증가 (360/n 개 구간) |
| `MIN_DIST_MM` | 200mm | 너무 작으면 노이즈 증가, 크면 근거리 데이터 손실 |
| `IMU_UPDATE_RATE` | 0.005s | 작을수록 각도 추적 정밀, CPU 사용률 증가 |
| `IMU_DEADZONE_THRESHOLD` | 0.5°/s | 작으면 민감하지만 드리프트 위험, 크면 반응 느림 |
| `CONFIDENCE_THRESHOLD` | 7점 | 높으면 엄격한 필터링, 낮으면 오인식 가능 |

---

## 🔧 의존성

프로젝트 의존성은 `requirements.txt`에 명시되어 있습니다:

```bash
# 패키지 설치
pip install -r requirements.txt
```

**주요 패키지:**
- **rplidar-roboticia** ≥0.17.0 - RPLiDAR 제어 및 데이터 수집
- **mpu9250-jmdev** ≥1.0.0 - MPU9250 IMU 센서 드라이버
- **python-socketio[client]** ≥5.0.0 - Socket.IO 클라이언트 (Flask 서버 통신)
- **numpy** ≥1.20.0 - 수치 계산 및 배열 처리

## 💡 주요 기능

1. **실시간 위치 추적**: LiDAR 스캔 데이터를 맵과 매칭하여 위치 추정 (전수 조사 알고리즘)
2. **각도 추적**: IMU(MPU9250) 자이로스코프를 사용한 정확한 방향 추적
   - 자이로 바이어스 자동 보정 (3초 캘리브레이션)
   - 각속도 적분을 통한 누적 각도 계산
   - 데드존 필터링으로 노이즈 감소
3. **스캔 데이터 처리**:
   - 하드웨어 노이즈 각도 범위 자동 제외
   - 최소 거리(200mm) 이하 데이터 필터링
   - ANGLE_STEP에 따른 각도 구간별 평균 거리 계산
4. **가상 스캔 미리 계산**: 맵의 모든 후보 위치에서 0도 기준 가상 LiDAR 데이터 사전 계산
5. **위치 매칭**: 실제 스캔과 가상 스캔의 거리 오차를 계산하여 최적 위치 선정
6. **신뢰도 평가**: 위치 추정 오차에 기반한 신뢰도 점수 (0-10)
7. **서버 통신**: Socket.IO를 통한 실시간 위치 및 상태 데이터 전송
8. **도난 경고**: 신뢰도가 임계값 이하일 때 경고 신호 전송

## 📝 참고사항

**시스템 요구사항:**
- Python 3.7 이상
- Linux 운영체제 (I2C, 시리얼 통신 지원)
- 하드웨어: Raspberry Pi5 또는 유사 보드 추천

**초기 설정:**
- 카트는 시작 시 맵의 0도(오른쪽 방향)를 정면으로 향해야 합니다
- IMU 보정 시 카트를 3초간 정지 상태로 유지하세요
- LiDAR를 `/dev/ttyUSB0` 포트에 연결하세요

**필터링:**
- 최소 거리(200mm) 이하의 데이터는 노이즈로 필터링됩니다
- 정의된 NOISE_ANGLE_RANGES의 각도 범위는 제외됩니다

**동작:**
- 맵 로드 및 스캔 데이터 미리 계산에 시간이 소요됩니다
- 신뢰도 점수가 CONFIDENCE_THRESHOLD 초과일 때 위치를 신뢰할 수 있습니다
- 신뢰도 점수가 CONFIDENCE_THRESHOLD 이하일 때는 도난 의심 경보를 보냅니다
- 초기 스캔3회는 시스템 안정화를 위해 스킵됩니다
- 서버 통신이 비활성화된 경우 로컬 모드로 작동합니다

## 👥 제작

**Team 4** - 2026년 1월 ~ 2월
