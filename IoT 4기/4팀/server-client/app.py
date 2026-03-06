# main.py
from flask import Flask, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
from config import Config
from database import DatabaseManager
from cart_manager import CartManager

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# --- 인스턴스 초기화 ---
db_manager = DatabaseManager()
cart_manager = CartManager(db_manager)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shoppingEnd')
def shopping_end():
    return render_template('shopping_end.html', finished_id=cart_manager.cart_id)

@app.route('/restartShopping')
def restart_shopping():
    cart_manager.restart_shopping()
    return redirect(url_for('index'))

# --- 소켓 이벤트 ---

@app.route('/update_full_state') # 혹은 socketio.on('update_full_state')
@socketio.on('update_full_state')
def handle_full_state(data):
    # 로직 매니저에게 데이터 전달
    should_broadcast = cart_manager.update_state(data)
    
    if should_broadcast:
        # 웹 브라우저 전송
        socketio.emit('sc_data', cart_manager.get_state())

@socketio.on('update_confidence')
def handle_confidence(data):
    cart_manager.handle_risk()
    val = data.get('confidence', 'Unknown')
    socketio.emit('show_warning', {'msg': '도난이 감지되었습니다!', 'confidence': val})

PRODUCT_PRICES = {
    "scissors": 1000,
    "remote": 3000,
    "mouse": 15000,
    "unknown": 0
}
cart_inventory = {}
# ---------------------------------------------------------
# [NEW] 3. 물품 감지 데이터 수신 -> 장바구니 리스트 업데이트
# ---------------------------------------------------------
# ---------------------------------------------------------
# [NEW] 물품 감지 -> 가격 계산 -> 웹으로 전송
# ---------------------------------------------------------
@socketio.on('update_item')
def handle_item_update(data):
    global cart_inventory
    
    item_name = data.get('item_name')
    
    if item_name:
        # 1. 수량 증가 로직
        if item_name in cart_inventory:
            cart_inventory[item_name] += 1
        else:
            cart_inventory[item_name] = 1
            
        print(f"🛒 장바구니 업데이트: {item_name} (총 {cart_inventory[item_name]}개)")

        # 2. 웹으로 보낼 데이터 가공 (리스트 형태 + 총액)
        receipt_data = []
        grand_total = 0
        
        for name, count in cart_inventory.items():
            price = PRODUCT_PRICES.get(name, 0) # 가격표에 없으면 0원
            total_price = price * count
            grand_total += total_price
            
            receipt_data.append({
                'name': name,
                'price': price,
                'count': count,
                'total': total_price
            })
        
        # 3. 변경된 영수증 정보 전송
        socketio.emit('update_receipt', {
            'items': receipt_data,
            'grand_total': grand_total
        })

if __name__ == '__main__':
    try:
        print("🚀 Server Started on port 8000...")
        socketio.run(app, host='0.0.0.0', port=8000, debug=False)
    finally:
        db_manager.close()
        print("InfluxDB 연결 종료")