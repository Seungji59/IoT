class Config:
    SECRET_KEY = 'secret!'
    
    # InfluxDB 설정
    INFLUXDB_URL = "http://192.168.0.4:8086"
    INFLUXDB_TOKEN = "YOUR_TOKEN"
    INFLUXDB_ORG = "4team"
    INFLUXDB_BUCKET = "4team"
    
    # 로직 설정
    RISK_TIMEOUT = 2  # 도난 차단 시간
    IGNORE_ZONES = [
        {'x': 0.0, 'y': 0.0, 'name': 'StartPoint'},
        {'x': 1.2, 'y': 1.2, 'name': 'EndPoint'}
    ]