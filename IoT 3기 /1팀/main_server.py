from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import logging

# 기능 모듈 임포트 (업로드된 파일명 기준)
from recommend_api import Recommender
from db_handler import DBHandler
from order_service import OrderService

# Flask 앱 및 로깅 설정
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")

# DB 설정 (mariadb 커넥터로 통일)
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '1234',
    'database': 'smart_cart_db',
}

# 기능 클래스 인스턴스 초기화
try:
    recommender_instance = Recommender(DB_CONFIG)
    db_handler_instance = DBHandler(DB_CONFIG)
    order_service_instance = OrderService(DB_CONFIG)
except Exception as e:
    log.error(f"시스템 초기화 실패: {e}")
    recommender_instance = None
    db_handler_instance = None
    order_service_instance = None

# ---- API ----

# 상품 추천 API
@app.route('/recommend', methods=['POST'])
def recommend():
    if not recommender_instance: 
        return jsonify(ok=False, error="추천 시스템 오류"), 500
    req = request.get_json(silent=True) or {}
    cart = req.get('cart', [])
    gender = req.get('gender')
    age = req.get('age')
    
    # 디버깅 로그 추가
    log.info(f"[추천 API] 요청 데이터 - 장바구니: {cart}, 성별: {gender}, 나이: {age}")
    
    if not all([cart, gender, age]):
        log.warning(f"[추천 API] 필수 필드 누락 - cart: {cart}, gender: {gender}, age: {age}")
        return jsonify(ok=False, error="필수 필드 누락"), 400
    try:
        recommendations = recommender_instance.recommend(cart, gender, int(age))
        log.info(f"[추천 API] 응답 데이터: {recommendations}")
        return jsonify(recommendations)
    except Exception as e:
        log.exception("추천 API 오류")
        return jsonify(ok=False, error=str(e)), 500

# 상품 조회 API
@app.route('/products', methods=['GET'])
def get_products():
    if not db_handler_instance: 
        return jsonify(ok=False, error="DB 핸들러 오류"), 500
    try:
        products = db_handler_instance.get_all_products()
        return jsonify(products)
    except Exception as e:
        log.exception("상품 조회 API 오류")
        return jsonify(ok=False, error=str(e)), 500

# 바코드 스캔 조회
@app.route('/api/scan', methods=['POST'])
def api_scan():
    if not order_service_instance: 
        return jsonify(ok=False, error="주문 시스템 오류"), 500
    d = request.get_json(silent=True) or {}
    barcode = (d.get("barcode") or "").strip()
    qty = int(d.get("qty") or d.get("quantity") or 1)
    if not barcode:
        return jsonify(ok=False, error="barcode_required"), 400
    try:
        product = order_service_instance.scan_product(barcode)
        if not product:
            return jsonify(ok=False, error="product_not_found"), 404
        product['qty'] = qty
        return jsonify(ok=True, **product)
    except Exception as e:
        log.exception("스캔 API 오류")
        return jsonify(ok=False, error=str(e)), 500

# 주문 결제
@app.route("/order/checkout", methods=['POST'])
@app.route("/checkout", methods=['POST'])
def checkout():
    if not order_service_instance: 
        return jsonify(ok=False, error="주문 시스템 오류"), 500
    p = request.get_json(silent=True) or {}
    try:
        result = order_service_instance.checkout_order(p)
        return jsonify(ok=True, **result), 200
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    except Exception as e:
        log.exception("결제 API 오류")
        return jsonify(ok=False, error=str(e)), 500

# CLI (선택)
def cli_product_lookup():
    if not db_handler_instance:
        print("DB 시스템 초기화 실패. CLI 사용 불가.")
        return
    while True:
        try:
            product_id_input = input("🔍 상품 코드를 입력하세요 (종료: q): ")
            if product_id_input.lower() == 'q':
                print("종료합니다.")
                break
            product_id = int(product_id_input)
            product_info = db_handler_instance.get_product_by_id(product_id)
            if product_info:
                print(f"📦 상품: {product_info['product_name']}, 💰 가격: {product_info['price']:,.0f}원, 수량: {product_info['quantity']}개")
            else:
                print("❌ 해당 상품이 없습니다.")
        except Exception as e:
            print(f"오류: {e}")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False))
    flask_thread.daemon = True
    flask_thread.start()
    cli_product_lookup()
