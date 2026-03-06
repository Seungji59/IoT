# Smart Cart 🛒

스마트 카트의 실시간 위치 추적 및 도난 감지 시스템입니다.

## 주요 기능

- 🗺️ **실시간 위치 추적**: 카트의 x, y 좌표 및 각도 실시간 모니터링
- 🎮 **3D 시각화**: Unity WebGL 기반 카트 실시간 3D 렌더링
- 🚨 **도난 감지**: 의심 행동 감지 시 경고 알림
- 💾 **데이터 저장**: InfluxDB를 활용한 시계열 데이터 저장
- 🔄 **쇼핑 세션 관리**: 카트별 고유 ID 부여 및 세션 관리
- 🌐 **실시간 통신**: WebSocket(Socket.IO)을 통한 양방향 통신

## 기술 스택

- **Backend**: Flask + Flask-SocketIO
- **Database**: InfluxDB (시계열 데이터베이스)
- **Frontend**: HTML/CSS/JavaScript (WebSocket 통신)
- **3D Visualization**: Unity WebGL
- **Language**: Python 3.x

## 프로젝트 구조

```
smart_cart/
├── app.py              # Flask 서버 및 라우팅
├── cart_manager.py     # 카트 상태 및 로직 관리
├── database.py         # InfluxDB 연결 및 데이터 관리
├── config.py           # 설정 파일
├── requirements.txt    # 패키지 의존성
└── static/             # 정적 파일
│   ├── Build/          # Unity WebGL 빌드 파일
│   │   ├── Cart_Project.data.unityweb
│   │   ├── Cart_Project.framework.js.unityweb
│   │   ├── Cart_Project.loader.js
│   │   └── Cart_Project.wasm.unityweb
│   ├── css/
│   │   └── dashboard.css
│   ├── js/
│   │   └── dashboard.js    # 대시보드 JavaScript
│   └── TemplateData/   # Unity 템플릿 리소스
└── templates/          # HTML 템플릿
    ├── index.html
    └── shopping_end.html
```

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd smart_cart
```

### 2. 가상환경 생성 (선택사항)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 설정

`config.py` 파일에서 InfluxDB 설정을 수정하세요:

```python
INFLUXDB_URL = "http://your-influxdb-url:8086"
INFLUXDB_TOKEN = "your-token"
INFLUXDB_ORG = "your-org"
INFLUXDB_BUCKET = "your-bucket"
```

## 실행 방법

```bash
python app.py
```

서버가 `http://localhost:8000`에서 시작됩니다.

## API 엔드포인트

### HTTP Routes

- `GET /` - 메인 페이지
- `GET /shoppingEnd` - 쇼핑 완료 페이지
- `GET /restartShopping` - 새로운 쇼핑 세션 시작

### WebSocket Events

#### 수신 이벤트

- `update_full_state` - 카트 상태 업데이트

  ```json
  {
    "x": 5.2,
    "y": 3.1,
    "angle": 45
  }
  ```

- `update_confidence` - 도난 감지 신뢰도 전달
  ```json
  {
    "confidence": 0.85
  }
  ```

#### 송신 이벤트

- `sc_data` - 현재 카트 상태 전송
- `show_warning` - 도난 경고 메시지 전송

## 주요 기능 설명

### 카트 ID 관리

각 쇼핑 세션마다 고유한 `cart_id`가 부여되며, InfluxDB에서 마지막 ID를 조회하여 자동으로 증가합니다.

### 도난 감지 메커니즘

- 도난이 감지되면 2초간 데이터 저장이 차단됩니다
- `RISK_TIMEOUT` 설정으로 차단 시간 조정 가능

### 제외 구역 설정

시작점(0.0~1.2, 0.0~1.2) 구역 내에서는 데이터가 DB에 저장되지 않습니다.

## 설정 옵션

`config.py`에서 다음 옵션을 조정할 수 있습니다:

- `RISK_TIMEOUT`: 도난 감지 후 데이터 차단 시간 (2초)
- `IGNORE_ZONES`: DB 저장을 제외할 구역 좌표
