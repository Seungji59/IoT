#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mariadb
from mariadb import Error
from datetime import date, datetime
import requests  # 알림 전송을 위한 HTTP 요청용

class OrderService:
    def __init__(self, db_config):
        allow = {"host", "port", "user", "password", "database", "unix_socket", "ssl", "connect_timeout", "autocommit"}
        self.db_config = {k: v for k, v in db_config.items() if k in allow}
        
        # 관리자 앱의 IP 주소 및 포트
        self.admin_notify_url = "http://127.0.0.1:5000/"

    def _db_connect(self):
        return mariadb.connect(**self.db_config)

    def scan_product(self, product_id):
        """Product 테이블에서 product_id로 상품 조회"""
        conn = None
        cur = None
        try:
            conn = self._db_connect()
            cur = conn.cursor()
            cur.execute("""
                SELECT product_id, product_name, price
                FROM Product
                WHERE product_id = ?
            """, (product_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "product_id": row[0],
                "name": row[1],
                "price": float(row[2]),
            }
        except Error as e:
            raise Exception(f"DB 오류: {e}")
        finally:
            if cur: cur.close()
            if conn: conn.close()

    def _send_stock_alert(self, product_id, product_name):
        """안드로이드 관리자 앱에 재고 부족 알림 전송"""
        try:
            msg = {
                "message": f"🔔 재고 알림: '{product_name}' (ID: {product_id})의 재고가 0개입니다."
            }
            requests.post(self.admin_notify_url, json=msg, timeout=2)
        except Exception as e:
            print("[경고] 관리자 알림 전송 실패:", e)

    def checkout_order(self, cart_data):
        """Purchase 테이블에 구매 내역 저장 및 Product 재고 차감"""
        conn = None
        cur = None
        try:
            conn = self._db_connect()
            cur = conn.cursor()

            p = cart_data
            cust = p.get("customer") or {}
            items = p.get("items") or []

            # 고객 정보 파싱 함수들
            def _age_from_birth(birthdate=None, birth_year=None):
                today = date.today()
                try:
                    if birthdate:
                        d = datetime.strptime(birthdate, "%Y-%m-%d").date()
                        return max(today.year - d.year - ((today.month, today.day) < (d.month, d.day)), 0)
                    if birth_year:
                        return max(today.year - int(birth_year), 0)
                except:
                    return None

            def _age_group_kr(age):
                if age is None: return None
                if age < 10: return "10대 미만"
                if age >= 60: return "60대 이상"
                return f"{(age//10)*10}대"

            def _norm_gender(g):
                if not g: return None
                g = str(g).strip().upper()
                if g in ("M", "남", "MALE"): return "남성"
                if g in ("F", "여", "FEMALE"): return "여성"
                return None

            customer_id = (cust.get("id") or cust.get("customer_id") or "").strip()
            gender = _norm_gender(cust.get("gender"))
            age = _age_from_birth(cust.get("birthdate"), cust.get("birth_year"))
            age_group = _age_group_kr(age)
            cart_id = int(p.get("cart_id") or 0)
            now = datetime.now()

            # 필수 값 체크
            if not customer_id or not items:
                raise ValueError("customer_id와 items는 필수 필드입니다.")
            if gender not in ("남성", "여성"):
                raise ValueError("gender는 '남성' 또는 '여성'이어야 합니다.")
            if age_group is None:
                raise ValueError("나이 정보가 유효하지 않습니다.")

            for item in items:
                # JSON에서 barcode로 받은 값을 product_id로 사용
                product_id = item.get("barcode")
                if not product_id:
                    raise ValueError("상품에 barcode 필드가 필요합니다.")
                product_id = int(product_id)
                quantity = int(item.get("qty") or item.get("quantity") or 1)

                # 구매내역 Purchase 테이블에 저장
                cur.execute("""
                    INSERT INTO Purchase (customerid, gender, age_group, cartid, product_id, quantity, purchase_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (customer_id, gender, age_group, cart_id, product_id, quantity, now))

                # 재고 차감
                cur.execute("""
                    UPDATE Product
                    SET quantity = quantity - ?
                    WHERE product_id = ? AND quantity >= ?
                """, (quantity, product_id, quantity))

                # 재고 부족 시 롤백
                if cur.rowcount == 0:
                    raise ValueError(f"상품 {product_id}의 재고가 부족합니다.")

                # 재고가 0이 되었는지 확인
                cur.execute("SELECT product_name, quantity FROM Product WHERE product_id = ?", (product_id,))
                row = cur.fetchone()
                if row and row[1] == 0:
                    product_name = row[0]
                    self._send_stock_alert(product_id, product_name)

            conn.commit()

            return {
                "cart_id": cart_id,
                "customer_id": customer_id,
                "gender": gender,
                "age_group": age_group,
                "total_items": len(items)
            }

        except Error as e:
            if conn: conn.rollback()
            raise Exception(f"DB 오류: {e}")
        except ValueError as e:
            if conn: conn.rollback()
            raise e
        finally:
            if cur: cur.close()
            if conn: conn.close()
