# database.py
from influxdb_client import InfluxDBClient, WriteOptions
from config import Config

class DatabaseManager:
    def __init__(self):
        self.client = InfluxDBClient(
            url=Config.INFLUXDB_URL, 
            token=Config.INFLUXDB_TOKEN, 
            org=Config.INFLUXDB_ORG
        )
        self.write_api = self.client.write_api(write_options=WriteOptions(
            batch_size=500,
            flush_interval=500,
            jitter_interval=0,
            retry_interval=5000
        ))
        self.query_api = self.client.query_api()

    def get_next_cart_id(self):
        # 기존 데이터에서 마지막 ID를 조회하여 다음 ID 반환
        try:
            query = f'''from(bucket:"{Config.INFLUXDB_BUCKET}") |> range(start: -1y)
                        |> filter(fn: (r) => r._measurement == "cart_state")
                        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                        |> group()
                        |> sort(columns: ["_time"], desc: true)
                        |> limit(n:1)'''
            tables = self.query_api.query(query, org=Config.INFLUXDB_ORG)
            last_val = tables[0].records[0].values.get("cart_id")
            return int(last_val) + 1
        except Exception as e:
            return 1

    def save_cart_state(self, cart_id, state):
        # 카트 상태 저장
        point = {
            "measurement": "cart_state",
            "tags": { "cart_id": cart_id },
            "fields": {
                "x": state['x'],
                "y": state['y'],
                "angle": state['angle']
            }
        }
        self.write_api.write(bucket=Config.INFLUXDB_BUCKET, record=point)

    def close(self):
        self.client.close()