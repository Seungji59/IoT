
from flask import Flask, jsonify, request
from flask_cors import CORS
from mysql.connector import pooling
import traceback
import paho.mqtt.client as mqtt
import json
import os

print("Flask server starting ...")

app = Flask(__name__)
CORS(app)

# MySQL Connection & Pool Configuration
dbconfig = {
    'host': '172.31.70.124',
    'user': 'root',
    'password': '123456',
    'database': 'smartpot'
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name='mypool',
    pool_size=10,
    pool_reset_session=True,
    **dbconfig
)

def get_db_connection():
    return connection_pool.get_connection()

# MQTT Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "192.168.0.10")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_CMD = os.getenv("TOPIC_CMD", "smartpot/display/set")

mq = mqtt.Client(client_id="flask-gateway")
mq.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
mq.loop_start()

ALLOWED = {"happy", "love", "neutral"}

@app.route("/mood", methods=["POST"])
def mood():
    try:
        body = request.get_json(force=True)
        mood = body.get("mood")

        if mood not in ALLOWED:
            return jsonify({"ok": False, "err": "invalid mood"}), 400

        duration_ms = int(body.get("duration_ms", 3000))
        msg = {"mood": mood, "duration_ms": duration_ms}

        info = mq.publish(TOPIC_CMD, json.dumps(msg), qos=1, retain=False)
        info.wait_for_publish(timeout=2.0)

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "err": str(e)}), 500

@app.route("/login", methods=['POST'])
def login():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user:
            if user["password"] == password:
                return jsonify({
                    "status": "success",
                    "user": {
                        "user_id": user["user_id"],
                        "username": user["username"],
                        "email": user["email"]
                    }
                }), 200
            else:
                return jsonify({"status": "error", "message": "Invalid password"}), 401
        else:
            return jsonify({"status": "error", "message": "User not found"}), 404

    except Exception as e:
        print("Login Error:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/check-email", methods=['POST'])
def check_email():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        email = data.get("email")

        if not email:
            return jsonify({'status': 'error', 'message': 'Email is required.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            return jsonify({'exists': True, 'message': 'Email already in use.'}), 409
        else:
            return jsonify({'exists': False, 'message': 'Email is available.'}), 200

    except Exception as e:
        print("Email Check Error:", e)
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/register", methods=['POST'])
def register():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        if not username or not email or not password:
            return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            return jsonify({'status': 'error', 'message': 'Email already registered.'}), 409

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password)
        )
        conn.commit()

        return jsonify({'status': 'success', 'message': 'Registration successful.'}), 200

    except Exception as e:
        print("Register Error:", e)
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/latest/<int:user_id>", methods=['GET'])
def get_latest_sensor_data_by_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        def fetch_latest(column):
            query = f"""
                SELECT {column}
                FROM sensor_data
                WHERE user_id = %s AND {column} IS NOT NULL
                ORDER BY recorded_at DESC
                LIMIT 1
            """
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            return result[column] if result else None

        temperature = fetch_latest("temperature")
        soil_moisture = fetch_latest("soil_moisture_pct")
        external_humidity = fetch_latest("external_humidity")
        light_lux = fetch_latest("light_lux")
        water_status = fetch_latest("water_level_status")

        return jsonify({
            "temperature": temperature,
            "soil_moisture_pct": soil_moisture,
            "external_humidity": external_humidity,
            "light_lux": light_lux,
            "water_level_status": water_status
        }), 200

    except Exception as e:
        print(f"[ERROR] /latest/{user_id} →", e)
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/user/<int:user_id>", methods=["GET"])
def get_user_profile(user_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, email, created_at FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if user:
            if isinstance(user["created_at"], (str, bytes)):
                created_at_str = user["created_at"]
            else:
                created_at_str = user["created_at"].strftime("%Y-%m-%d %H:%M:%S")

            return jsonify({
                "username": user["username"],
                "email": user["email"],
                "created_at": created_at_str
            }), 200
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        print("Error in /user/<user_id>:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)